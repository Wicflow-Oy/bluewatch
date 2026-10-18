"""Pre-company leads from public data, in the same shape as a team's own submission.

- Hackathon results: the scout's top projects (bluewatch/scout), with the organiser's results page as the
  public record and the scout's organisation-level routes. Youth and school events are already excluded.
- Research projects: EU and Interreg projects from data/seed/research_prestartup.json that the research
  file rates Strong or Medium for start-up fit (plus its two reach examples), still running.

Nothing here is a student submission and nothing is invented: every lead keeps its source link, and the
"submission" built from it holds only text the record itself states. Organisations only: no person's
name or contact details are read or kept.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from bluewatch import seed
from bluewatch.ideas.models import IdeaSubmission, LedgerItem, Origin, PresetName, SimilarItem
from bluewatch.ideas.text import content_words, similarity
from bluewatch.models import HackathonProject, NextCheck, Route
from bluewatch.rules.text import parse_date
from bluewatch.scout import plans as scout_plans
from bluewatch.scout.projects import load_projects
from bluewatch.scout.score import is_concept

HACKATHON_LEADS = 12
TITLE_MAX = 80  # IdeaSubmission's limit for a title
RESEARCH_TIERS = ("Strong", "Medium", "Local (non-CORDIS)", "EU (outside FI)")
SIMILAR = 0.5  # content-word overlap at which two ideas are flagged as near-duplicates
CHECKED = "Checked 17 Oct 2026"
EVENT_DAYS = re.compile(r"(\d{4}-\d\d-\d\d)(?:\s*(?:to|/)\s*(\d{4}-\d\d-\d\d))?")
PARTICIPANT_TYPES = {"REC": "research", "HES": "university", "PRC": "company", "PUB": "public body"}
LEGAL_FORMS = {"OY": "Oy", "AB": "Ab", "RF": "rf"}
SMALL_WORDS = frozenset({"OF", "AND", "FOR", "THE", "BY", "ON", "IN", "TO", "AT"})


@dataclass(frozen=True)
class PublicIdea:
    id: str
    submission: IdeaSubmission
    origin: Origin
    facts: tuple[LedgerItem, ...]
    assumptions: tuple[LedgerItem, ...]
    unknowns: tuple[LedgerItem, ...]
    questions: tuple[str, ...]
    route: Route | None  # the organisation asked to forward the invitation
    team_label: str
    why: tuple[str, ...]
    source_rank: int  # the order its own source gives it
    description: str  # the public text about the project itself: what a read may quote
    title_only: bool = False  # only a title is public in our data (research projects)


def _fact(lead_id: str, n: int, text: str, source: str, url: str | None) -> LedgerItem:
    return LedgerItem(id=f"{lead_id}:fact:{n}", field="record", state="fact", text=text, source=source, source_url=url)


def day(iso: str) -> str:
    """A record's ISO day as the app writes dates in prose ("01 Apr 2023"); anything else stays as it is."""
    d = parse_date(iso)
    return f"{d:%d %b %Y}" if d else iso


def _event_dates(text: str | None) -> str | None:
    """The event's day or days from the scout's date field, which may also hold research notes: only the
    leading date or date range is kept, and a month or year alone is left out."""
    m = EVENT_DAYS.match((text or "").strip())
    if not m:
        return None
    return day(m.group(1)) + (f" to {day(m.group(2))}" if m.group(2) else "")


def _invite_route(routes: list[Route]) -> Route | None:
    return next((r for r in routes if r.kind in ("organiser", "university_office")), None)


def _short(text: str, limit: int) -> str:
    """The text cut at a word boundary to fit `limit`, marked with an ellipsis when cut."""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(" -:,") + "…"


def _hackathon(project: HackathonProject, plan, rank: int, preset: PresetName) -> PublicIdea:
    lead_id = f"hackathon:{project.id}"
    url = scout_plans.public_url(project.source_url)
    owner = scout_plans.CHALLENGE_OWNER.search(project.idea or "")
    source = "Organiser's results page"
    name = scout_plans.project_name(project)
    sub = IdeaSubmission(
        title=_short(name, TITLE_MAX),
        who_has_it=((owner.group(1) or owner.group(2)).strip() if owner else "")[:300],
        solution=(project.idea or "")[:800],
        exists=["concept"] if is_concept(project) else ["prototype"],
        preset=preset,
    )
    facts = [f"{project.placement or 'Listed'} at {scout_plans.short_event(project)}"]
    when = _event_dates(project.date)
    facts += [f"Date: {when}"] if when else []
    where = scout_plans.place(project)
    facts += [f"Place: {where}"] if where else []
    route = _invite_route(plan.route_ladder)
    facts += [f"Organiser: {route.organisation}"] if route and route.kind == "organiser" else []
    unknowns = tuple(
        LedgerItem(
            id=g.id,
            field=g.field,
            state="unknown",
            text=g.claim,
            source=source,
            source_url=url,
            next_check=g.next_check,
        )
        for g in plan.gaps
    )
    parts = sorted(plan.promise_score.parts.items(), key=lambda kv: -kv[1])[:2]
    why = [
        f"{project.placement or 'Listed'} at {scout_plans.short_event(project)}",
        f"Promise score {plan.promise_score.total:.0f} of 100 from public facts (a ranking aid, not a "
        f"prediction); most from {' and '.join(k.replace('_', ' ') for k, _ in parts)}",
    ]
    warm = next((r for r in plan.route_ladder if r.kind == "warm_intro"), None)
    if warm:
        why.append(f"Warm route: {warm.organisation}")
    origin = Origin(kind="hackathon_result", label="Public hackathon result", url=url, checked=CHECKED, facts=facts)
    return PublicIdea(
        id=lead_id,
        submission=sub,
        origin=origin,
        facts=tuple(_fact(lead_id, i, t, source, url) for i, t in enumerate(facts)),
        assumptions=(),
        unknowns=unknowns,
        questions=tuple(plan.questions[:2]),
        route=route,
        team_label=scout_plans.team_phrase(project),
        why=tuple(why),
        source_rank=rank,
        description=project.idea or "",
    )


def hackathon_ideas(preset: PresetName, today: date) -> list[PublicIdea]:
    projects = {p.id: p for p in load_projects()}
    plans = scout_plans.plans(top_n=HACKATHON_LEADS, today=today)
    return [_hackathon(projects[plan.project_id], plan, i, preset) for i, plan in enumerate(plans, 1)]


def org_name(raw: str) -> str:
    """CORDIS prints names in capitals: "TEKNOLOGIAN TUTKIMUSKESKUS VTT OY" -> "Teknologian Tutkimuskeskus VTT Oy".
    Three-letter words stay in capitals because they are usually acronyms (VTT, LUT)."""
    if not raw.isupper():
        return raw

    def word(w: str) -> str:
        if w in LEGAL_FORMS:
            return LEGAL_FORMS[w]
        return w if len(w) <= 3 and w not in SMALL_WORDS else w.title()

    return " ".join(word(w) for w in raw.split())


def _participants(row: dict) -> list[str]:
    return [
        f"{org_name(p['name'])} ({PARTICIPANT_TYPES.get(p.get('type'), 'organisation')})"
        for p in row.get("finnish_participants") or []
    ]


def _research_route(row: dict) -> Route:
    finnish = row.get("finnish_participants") or []
    academic = next((p for p in finnish if p.get("type") in ("REC", "HES")), None)
    org = academic or (finnish[0] if finnish else row["coordinator"])
    return Route(
        rank=1,
        kind="university_office" if academic else "organiser",
        organisation=f"{org_name(org['name'])} (innovation or research services)",
        how="Ask the office to pass the Idea Harbour invitation to the project team",
    )


def _research(row: dict, rank: int, preset: PresetName) -> PublicIdea:
    lead_id = f"research:{row.get('grant_agreement_id') or row['acronym']}"
    url = row.get("cordis_url") or row.get("source_url")
    source = "CORDIS project record" if row.get("cordis_url") else "Programme project page"
    title = row["title"].capitalize() if row["title"].isupper() else row["title"]
    sub = IdeaSubmission(title=row["acronym"][:80], solution=title[:800], exists=["research"], preset=preset)
    scheme = " ".join(row["funding_scheme"].split())
    facts = [
        scheme + (f", call {row['call']}" if row.get("call") else ""),
        f"Runs {day(row['start'])} to {day(row['end'])}",
        f"Coordinator: {org_name(row['coordinator']['name'])} ({row['coordinator']['country']})",
    ]
    if _participants(row):
        facts.append(f"Finnish participants: {', '.join(_participants(row))}")
    assumption = LedgerItem(
        id=f"{lead_id}:assume:company",
        field="company",
        state="assumption",
        text=row["why_could_become_company"],
        source="BlueWatch research file",
        basis="An analyst's reading of the project record (re-checked 17 Oct 2026), not the project's own claim",
    )
    asks = (
        (
            "rights",
            "Who owns the results: unknown (open code or a paper is not a licence)",
            "Who owns the results, and may a team use them in a company?",
        ),
        (
            "company",
            "Whether anyone in the project plans a company",
            "Is anyone in the project team thinking of starting a company from it?",
        ),
    )
    unknowns = tuple(
        LedgerItem(
            id=f"{lead_id}:gap:{f}",
            field=f,
            state="unknown",
            text=t,
            source=source,
            source_url=url,
            next_check=NextCheck(kind="ask_founder", question=q),
        )
        for f, t, q in asks
    )
    origin = Origin(
        kind="research_project",
        label="EU research project" if row.get("cordis_url") else "Interreg research project",
        url=url,
        checked=CHECKED,
        facts=facts,
    )
    why = (
        f"{scheme} project, running until {day(row['end'])}",
        f"Start-up fit in the research file: {row['tier']}",
        f"Route: {_research_route(row).organisation}",
    )
    return PublicIdea(
        id=lead_id,
        submission=sub,
        origin=origin,
        facts=tuple(_fact(lead_id, i, t, source, url) for i, t in enumerate(facts)),
        assumptions=(assumption,),
        unknowns=unknowns,
        questions=tuple(q for _, _, q in asks),
        route=_research_route(row),
        team_label=f"the {row['acronym']} project team",
        why=why,
        source_rank=rank,
        description=title,
        title_only=True,
    )


def research_ideas(preset: PresetName) -> list[PublicIdea]:
    rows = [
        r
        for r in seed.load("research_prestartup")["projects"]
        if r["tier"] in RESEARCH_TIERS and r["status_on_2026_10_16"] == "running"
    ]
    return [_research(row, i, preset) for i, row in enumerate(rows, 1)]


@lru_cache(maxsize=4)
def public_ideas(preset: PresetName, today: date) -> tuple[PublicIdea, ...]:
    return tuple(hackathon_ideas(preset, today) + research_ideas(preset))


def idea_words(sub: IdeaSubmission) -> frozenset[str]:
    return content_words(f"{sub.title} {sub.problem} {sub.who_has_it} {sub.solution}")


def similar_public(sub: IdeaSubmission, today: date) -> list[SimilarItem]:
    """Public projects that read like this idea, so A'Pelago sees the overlap and the team sees prior work."""
    mine = idea_words(sub)
    scored = [(similarity(mine, idea_words(p.submission)), p) for p in public_ideas(sub.preset, today)]
    return [
        SimilarItem(id=p.id, title=p.submission.title, source=p.origin.label)
        for score, p in sorted(scored, key=lambda sp: -sp[0])
        if score >= SIMILAR
    ][:2]
