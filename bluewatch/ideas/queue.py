"""A'Pelago's review queue: ideas shared from this browser session plus pre-company leads from public data,
ranked by the same rubric, with near-duplicates flagged and a Top N cut, so the team reviews a handful.

The sample-data preview is a separate queue: the invented ideas in data/ideas/sample_ideas.json, read by
the same rules and labelled as samples. It never mixes with the live queue.

Ranking is reproducible and has no hidden score: tier first (Bring now, Promising, Not yet), then the
potential and evidence bands (A'Pelago mode reads potential first, Redstone mode evidence first), then each
source's own order (the scout's promise score, the research file's start-up fit), interleaving the sources,
with own submissions first on a tie. Held, low-effort and duplicate items stay in the list but never enter
the Top N, and the Top N is never padded.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import lru_cache

from bluewatch.config import DATA_DIR
from bluewatch.ideas import public_reads
from bluewatch.ideas.models import (
    Flag,
    IdeaAssessment,
    IdeaQueue,
    IdeaStep,
    IdeaSubmission,
    Invite,
    Origin,
    PresetName,
    QueueItem,
)
from bluewatch.ideas.pipeline import SIMILAR, PublicIdea, idea_words, public_ideas
from bluewatch.ideas.store import TTL_S, SharedIdea
from bluewatch.ideas.text import similarity
from bluewatch.ideas.vet import assess, vet

TIER_ORDER = {"bring_now": 0, "ask_two": 1, "not_yet": 2}
POTENTIAL_ORDER = {"high": 0, "medium": 1, "unknown": 2, "low": 3}  # unjudged ranks above judged-low
EVIDENCE_ORDER = {"strong": 0, "some": 1, "thin": 2}
SOURCE_ORDER = {"your_submission": 0, "hackathon_result": 1, "research_project": 2}
POTENTIAL_WORDS = {"high": "high", "medium": "medium", "low": "low", "unknown": "not judged yet"}
DEFAULT_TOP_N = 5
MAX_TOP_N = 10
NOT_TOP_FLAGS = {"held_instructions", "low_effort", "near_duplicate"}
BASE_RATE_NOTE = (
    "The tiers are rules applied to what is written, not predictions. There is no outcome data yet, so nobody "
    "can say how many 'Bring now' ideas become companies; the first cohort starts that record."
)
INVITE_NOTE = (
    "Sending is off in this workspace, so nothing is sent. When it is on, a person approves the "
    "message and the outreach desk sends it to the organisation's own channel; the team decides "
    "whether to reply."
)
SAMPLE_PATH = DATA_DIR / "ideas" / "sample_ideas.json"
SESSION_ORIGIN = "Your submission (this browser session)"
SAMPLE_ORIGIN = "Sample submission (invented)"


@dataclass(frozen=True)
class Candidate:
    """One idea on its way into the queue, before ranking."""

    sort_key: tuple
    item: QueueItem
    words: frozenset[str]


def invite(public: PublicIdea, questions: list[str]) -> Invite | None:
    if public.route is None:
        return None
    asks = " ".join(f"{i}) {q}" for i, q in enumerate(questions, 1))
    message = (
        f"Hello {public.route.organisation}: A'Pelago runs Idea Harbour, an opt-in programme for student and "
        f"research teams in the blue economy. Could you forward this invitation to {public.team_label}? They can "
        "describe their idea in a few minutes and get an honest readiness read; nothing reaches A'Pelago unless "
        f"they choose to share it. Two questions we would ask: {asks}"
    )
    return Invite(route=public.route, message=message, note=INVITE_NOTE)


def _invite_step(public: PublicIdea) -> IdeaStep | None:
    if public.route is None:
        return None
    return IdeaStep(
        rank=0,
        kind="invite",
        title=f"Invite via {public.route.organisation}",
        action=public.route.how,
        why="An organisation forwards the invitation; the team decides whether to reply.",
        source_url=public.route.contact_page_url,
    )


@lru_cache(maxsize=4)
def _public_items(preset: PresetName, today: date) -> tuple[tuple[PublicIdea, IdeaAssessment], ...]:
    """Public leads are the same for every visitor, so they are assessed once per preset and day, from
    Claude's recorded reads where there is one (public_reads.py); no model is called here."""
    out = []
    for p in public_ideas(preset, today):
        sub, claims, reader, note = public_reads.prepared(p)
        out.append(
            (
                p,
                assess(
                    sub,
                    claims,
                    flags=[],
                    today=today,
                    public=p,
                    invite_step=_invite_step(p),
                    reader=reader,
                    reader_note=note,
                ),
            )
        )
    return tuple(out)


def _sort_key(mode: str, a: IdeaAssessment, source: str, source_rank: int) -> tuple:
    bands = (POTENTIAL_ORDER[a.potential], EVIDENCE_ORDER[a.evidence])
    return (TIER_ORDER[a.tier], *(bands if mode == "apelago" else bands[::-1]), source_rank, SOURCE_ORDER[source])


def _why_mode(mode: str, a: IdeaAssessment) -> str:
    areas = f"; impact: {', '.join(a.impact_areas)}" if a.impact_areas else ""
    if mode == "redstone":
        return f"Evidence {a.evidence}, potential {POTENTIAL_WORDS[a.potential]}{areas}"
    return f"Potential {POTENTIAL_WORDS[a.potential]}, evidence {a.evidence}{areas}"


def build_queue(
    mode: str, preset: PresetName, shared: list[SharedIdea], *, today: date, top_n: int = DEFAULT_TOP_N
) -> IdeaQueue:
    """The live queue: this session's shared ideas and the public leads. Never an invented submission."""
    candidates = [*_session_candidates(mode, shared), *_public_candidates(mode, preset, today)]
    return _ranked(mode, preset, candidates, top_n=top_n, session_items=len(shared))


def build_sample_queue(mode: str, preset: PresetName, *, today: date, top_n: int = DEFAULT_TOP_N) -> IdeaQueue:
    """The sample-data preview: the invented sample ideas only, read by the same rules (no model)."""
    candidates = [
        _candidate(
            mode,
            f"sample:{sample_id}",
            Origin(kind="your_submission", label=SAMPLE_ORIGIN, facts=[sample_label()]),
            sub,
            a,
            rank,
        )
        for rank, (sample_id, sub, a) in enumerate(_sample_reads(preset, today), 1)
    ]
    return _ranked(mode, preset, candidates, top_n=top_n, session_items=0, sample=True)


def _candidate(
    mode: str, item_id: str, origin: Origin, sub: IdeaSubmission, a: IdeaAssessment, source_rank: int
) -> Candidate:
    """A team's own (or sample) submission: why it is here is its bands, tier rule and best strength."""
    item = QueueItem(
        rank=0, id=item_id, origin=origin, assessment=a, why_here=[_why_mode(mode, a), a.tier_rule, *a.strengths[:1]]
    )
    return Candidate(_sort_key(mode, a, origin.kind, source_rank), item, idea_words(sub))


def _session_candidates(mode: str, shared: list[SharedIdea]) -> list[Candidate]:
    origin = Origin(
        kind="your_submission",
        label=SESSION_ORIGIN,
        facts=[
            f"Simulated share with consent: kept in this server's memory for {TTL_S // 60} minutes, "
            "visible only to this browser session; A'Pelago does not receive it"
        ],
    )
    return [
        _candidate(mode, f"session:{idea.assessment.id}", origin, idea.submission, idea.assessment, rank)
        for rank, idea in enumerate(shared, 1)
    ]


def _public_candidates(mode: str, preset: PresetName, today: date) -> list[Candidate]:
    out = []
    for public, a in _public_items(preset, today):
        item = QueueItem(
            rank=0,
            id=public.id,
            origin=public.origin,
            assessment=a,
            why_here=[_why_mode(mode, a), *public.why],
            invite=invite(public, a.questions),
        )
        out.append(
            Candidate(_sort_key(mode, a, public.origin.kind, public.source_rank), item, idea_words(public.submission))
        )
    return out


@lru_cache(maxsize=1)
def _sample_file() -> dict:
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def sample_label() -> str:
    return _sample_file()["label"]


@lru_cache(maxsize=4)
def _sample_reads(preset: PresetName, today: date) -> tuple[tuple[str, IdeaSubmission, IdeaAssessment], ...]:
    """Every sample idea of the preset, read once per day by the rules alone."""
    fields = IdeaSubmission.model_fields
    subs = [
        (raw["sample_id"], IdeaSubmission.model_validate({k: v for k, v in raw.items() if k in fields}))
        for raw in _sample_file()["ideas"]
    ]
    return tuple((sample_id, sub, vet(sub, today=today)) for sample_id, sub in subs if sub.preset == preset)


def _ranked(
    mode: str, preset: PresetName, candidates: list[Candidate], *, top_n: int, session_items: int, sample: bool = False
) -> IdeaQueue:
    top_n = max(1, min(top_n, MAX_TOP_N))
    items: list[QueueItem] = []
    seen: list[tuple[str, str, frozenset[str]]] = []
    for rank, c in enumerate(sorted(candidates, key=lambda c: c.sort_key), 1):
        item = c.item
        twin = next(((i, t) for i, t, w in seen if similarity(c.words, w) >= SIMILAR), None)
        if twin:
            flag = Flag(kind="near_duplicate", text=f"Reads like {twin[1]}, which ranks higher.")
            item = item.model_copy(
                update={
                    "duplicate_of": twin[0],
                    "assessment": item.assessment.model_copy(update={"flags": [*item.assessment.flags, flag]}),
                }
            )
        seen.append((item.id, item.assessment.title, c.words))
        items.append(item.model_copy(update={"rank": rank}))

    eligible = [
        i for i in items if i.assessment.tier != "not_yet" and not {f.kind for f in i.assessment.flags} & NOT_TOP_FLAGS
    ]
    top = eligible[:top_n]
    top_ids = {i.id for i in top}
    items = [i.model_copy(update={"in_top": i.id in top_ids}) for i in items]
    return IdeaQueue(
        mode=mode,
        preset=preset,
        generated_at=datetime.now(timezone.utc),
        top_n=top_n,
        top_ids=[i.id for i in top],
        why_these=why_these(len(top), len(items), top_n, sample=sample),
        why_not_next=_why_not_next(eligible[top_n:]),
        items=items,
        counts=_counts(items),
        facets=_facets(items),
        session_items=session_items,
        base_rate_note=BASE_RATE_NOTE,
        sample=sample,
        sample_label=sample_label() if sample else None,
    )


def why_these(chosen: int, total: int, top_n: int, *, sample: bool) -> str:
    what = "sample ideas" if sample else "ideas and leads"
    text = (
        f"Top {chosen} of {total} {what}: 'Bring to A'Pelago now' first, then 'Promising: ask two "
        "questions'. Held, low-effort and duplicate items stay in the full list but never enter the top."
    )
    empty = top_n - chosen
    if empty:
        text += f" Only {chosen} qualified, so {empty} {'slot stays' if empty == 1 else 'slots stay'} empty."
    return text


def _why_not_next(rest: list[QueueItem]) -> str | None:
    if not rest:
        return None
    nxt = rest[0].assessment
    return next_in_line(rest[0].rank, nxt.tier_label, nxt.potential, nxt.evidence)


def next_in_line(rank: int, tier_label: str, potential: str, evidence: str) -> str:
    """The first idea below the cut, by its rank: the list shows its title, and a sentence without a team's own
    title has a translation."""
    return f"Next in line: #{rank} ({tier_label}; potential {POTENTIAL_WORDS[potential]}, evidence {evidence})."


def _counts(items: list[QueueItem]) -> dict[str, int]:
    counts = Counter(i.assessment.tier for i in items) + Counter(i.origin.kind for i in items)
    return {
        "total": len(items),
        **counts,
        "held": sum(any(f.kind == "held_instructions" for f in i.assessment.flags) for i in items),
    }


def _facets(items: list[QueueItem]) -> dict[str, dict[str, int]]:
    return {
        "stage": dict(Counter(i.assessment.stage for i in items)),
        "impact_area": dict(Counter(a for i in items for a in i.assessment.impact_areas)),
        "need": dict(Counter(n for i in items for n in i.assessment.needs)),
        "source": dict(Counter(i.origin.kind for i in items)),
        "tier": dict(Counter(i.assessment.tier for i in items)),
    }
