"""Idea Harbour API: the student form and readiness read, consent-based sharing, and A'Pelago's queue.

- POST bodies only, at most 16 KB each, every field size-limited; rate-limited per IP like the founder view.
- /vet stores and logs nothing. The text goes to Claude only when the team ticks "Claude may read our
  answers too" (ai_read) and the server allows it; otherwise it never leaves this process.
- Only /share (explicit consent) keeps an idea, in this process's memory for 60 minutes, visible to the
  same browser session only (X-Demo-Session, a random id the browser keeps per tab). /withdraw removes it
  at once, and /shared tells a reloaded page that there is something to withdraw.
- Sharing is simulated: there is no partner handoff, so nothing is ever sent to A'Pelago. Every text the
  team reads (consent, receipt, withdraw) says so.
- The queue mixes that session's shared ideas with real pre-company leads from public data, each labelled
  with its source; it never shows invented student submissions.
- The sample-data preview (/queue?sample=1) is a separate queue of invented ideas, read by the same rules
  and marked sample: true with its label. It never mixes with the live queue.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel

from bluewatch.api import deps
from bluewatch.api.deps import ModeParam, PresetParam
from bluewatch.api.sessions import SESSION_ID
from bluewatch.config import settings
from bluewatch.i18n import Lang, LangParam, Translate, localize, localize_text
from bluewatch.ideas import queue as queue_mod
from bluewatch.ideas import rubric, signals, store, vet
from bluewatch.ideas.models import (
    LIMITS,
    IdeaAssessment,
    IdeaForm,
    IdeaQueue,
    IdeaSubmission,
    Option,
    RubricCriterion,
    RubricInfo,
    SessionShares,
    ShareReceipt,
    ShareRequest,
    WithdrawReceipt,
)
from bluewatch.models import ShareConsent

MAX_BODY_BYTES = 16_000
CONSENT_TEXT_VERSION = "idea-share-v3-2026-10-18"
# Both boxes speak in the team's own voice ("we", "our"), in English, Finnish and Swedish alike.
CONSENT_TEXT = (
    "We agree to add this idea and its readiness read to the demo review queue. Sharing is simulated in this "
    "prototype: A'Pelago does not receive it. We can withdraw at any time."
)
PRIVACY_NOTE = (
    "Nothing you type is stored or logged unless you choose to share it. Don't enter names, e-mail addresses "
    "or phone numbers: describe the team by roles."
)
AI_READ_TEXT = (
    "Claude may read our answers too. Our text is sent to Anthropic's API for this read only, and nothing is stored."
)
AI_READ_OFF_NOTE = "Claude reading is switched off on this server right now, so the rules read your answers."
SESSION_SHARE_NOTE = (
    "Added to the demo review queue, not sent to A'Pelago. Sharing is simulated in this prototype: only this "
    f"browser session can see it, for up to {store.TTL_S // 60} minutes. Sharing it again after an edit replaces it."
)
FILE_SHARE_NOTE = "Added to the review file on this server, not sent to A'Pelago: this prototype delivers nothing."


class LimitedBodyRoute(APIRoute):
    """Refuses a POST body over MAX_BODY_BYTES before it is parsed: a declared length before anything is read,
    and the body itself while it streams in (deps.read_capped), so the cap holds whatever the headers say."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def limited(request: Request):
            length = request.headers.get("content-length")
            if request.headers.get("transfer-encoding") or (length is not None and not length.isdigit()):
                raise HTTPException(status_code=411, detail="Send the form as JSON with a Content-Length.")
            if request.method == "POST":
                # Starlette's own cache for the body, so FastAPI parses these capped bytes and reads nothing more.
                request._body = await deps.read_capped(
                    request, MAX_BODY_BYTES, "The form is too long: keep each answer short."
                )
            return await handler(request)

        return limited


router = APIRouter(prefix="/api/ideas", route_class=LimitedBodyRoute)
_shared = store.SharedIdeas()


def rate_check(request: Request) -> None:
    deps.rate_check(
        request,
        "Too many idea checks from here right now. Wait a few minutes and try again; the review queue still works.",
    )


def session_id(x_demo_session: str = Header(...)) -> str:
    if not SESSION_ID.fullmatch(x_demo_session):
        raise HTTPException(status_code=422, detail="The session id must be 16 to 64 letters, digits or dashes.")
    return x_demo_session


def optional_session_id(x_demo_session: str | None = Header(None)) -> str | None:
    return x_demo_session if x_demo_session and SESSION_ID.fullmatch(x_demo_session) else None


RateLimited = Depends(rate_check)
Session = Annotated[str, Depends(session_id)]


def _checked(sub: IdeaSubmission) -> IdeaSubmission:
    if sub.impact_area and sub.impact_area not in signals.impact_areas(sub.preset):
        raise HTTPException(status_code=422, detail="Pick an impact area from the list, or 'Not sure'.")
    return sub


# Generic field names the i18n whitelist leaves alone, because elsewhere they hold names and enum keys. In
# Idea Harbour's answers they are prose the rules write: the title of a check or invite step (other steps
# are titled with a programme's name), a programme's status line, and where a ledger line or a similar
# idea came from.
RULE_TITLED_STEPS = frozenset({"check", "invite"})
# A strength quotes the team: 'Problem and who has it: Says who has it ("Fish farmers.")'. No table can hold the
# team's words, so the rule part is translated on its own and the quote goes back in Finnish and Swedish marks.
QUOTED_STRENGTH = re.compile(r'(?P<rule>.+?) \("(?P<quote>.*)"\)', re.S)
M = TypeVar("M", bound=BaseModel)


def idea_prose(data: object, translate: Translate) -> object:
    """JSON from an Idea Harbour answer with those fields passed through `translate`."""
    if isinstance(data, list):
        return [idea_prose(item, translate) for item in data]
    if not isinstance(data, dict):
        return data
    out = {key: idea_prose(value, translate) for key, value in data.items()}
    for key in ("strengths", "why_here"):
        if isinstance(out.get(key), list):
            out[key] = [quoted_strength(text, translate) for text in out[key]]
    for step in out.get("next_steps") or []:
        if step["kind"] in RULE_TITLED_STEPS:
            step["title"] = translate(step["title"])
        if step.get("status"):
            step["status"] = translate(step["status"])
    ledger = out.get("ledger")
    sourced = [item for items in ledger.values() for item in items] if isinstance(ledger, dict) else []
    for item in [*sourced, *(out.get("similar_to") or [])]:
        item["source"] = translate(item["source"])
    return out


def quoted_strength(text: str, translate: Translate) -> str:
    """A strength still in English because it quotes the team, with its rule translated and the quote in ”…”;
    any other text as it is."""
    found = QUOTED_STRENGTH.fullmatch(text)
    return f"{translate(found['rule'])} (”{found['quote']}”)" if found else text


def _localized(answer: M, lang: Lang) -> M:
    """The answer in `lang`: the whitelisted prose fields, then Idea Harbour's own (see idea_prose)."""
    out = localize(answer, lang)
    if lang == "en":
        return out
    return type(out).model_validate(idea_prose(out.model_dump(mode="json"), lambda text: localize_text(text, lang)))


@router.get("/form")
def form(preset: PresetParam, lang: LangParam = "en") -> IdeaForm:
    """Everything the form needs: options, limits, consent text, and whether a model reads the text."""

    def options(labels: dict[str, str]) -> list[Option]:
        return [Option(value=k, label=v) for k, v in labels.items()]

    return localize(
        IdeaForm(
            preset=preset,
            impact_areas=[Option(value=a, label=a) for a in signals.impact_areas(preset)],
            exists=options(rubric.EXISTS_LABELS),
            needs=options(
                {
                    "mentors": "Mentors",
                    "pilot_partner": "A pilot partner",
                    "funding": "Funding",
                    "team": "Team members",
                    "test_access": "Test or lab access",
                }
            ),
            roles=[
                Option(value="build", label="Builds it", hint="engineering, software, hardware"),
                Option(value="business", label="Sells it", hint="business, sales, finance"),
                Option(value="domain", label="Knows the field", hint="marine science, industry experience"),
                Option(value="design", label="Designs it", hint="product, service or industrial design"),
            ],
            commitment=options({"full_time": "Full time", "part_time": "Part time", "side_project": "Side project"}),
            countries=options(
                {
                    "FI": "Finland",
                    "SE": "Sweden",
                    "NO": "Norway",
                    "EE": "Estonia",
                    "DK": "Denmark",
                    "other": "Elsewhere",
                }
            ),
            limits=LIMITS,
            consent_text=CONSENT_TEXT,
            consent_text_version=CONSENT_TEXT_VERSION,
            privacy_note=PRIVACY_NOTE,
            model_reading=vet.model_enabled(),
            ai_read_text=AI_READ_TEXT,
            ai_read_off_note="" if vet.model_enabled() else AI_READ_OFF_NOTE,
        ),
        lang,
    )


@router.get("/rubric")
def rubric_info(lang: LangParam = "en") -> RubricInfo:
    return localize(
        RubricInfo(
            version=rubric.RUBRIC_VERSION,
            criteria=[
                RubricCriterion(
                    id=c.id,
                    label=c.label,
                    axis=c.axis,
                    weight=c.weight,
                    rungs=list(c.rungs),
                    rule=c.rule,
                    question=c.question,
                )
                for c in rubric.CRITERIA
            ],
            potential_rule=rubric.POTENTIAL_RULE,
            evidence_rule=rubric.EVIDENCE_RULE,
            tier_rules=list(rubric.TIER_RULES),
            anti_gaming=list(rubric.ANTI_GAMING),
        ),
        lang,
    )


@router.post("/vet", dependencies=[RateLimited])
def vet_idea(sub: IdeaSubmission, lang: LangParam = "en") -> IdeaAssessment:
    """The readiness read. Nothing is stored or logged; the text goes to Claude only with ai_read (see vet.py)."""
    model, note = vet.model_for(sub.ai_read)
    return _localized(vet.vet(_checked(sub), model=model, reader_note=note), lang)


@router.post("/share", dependencies=[RateLimited])
def share(body: ShareRequest, sid: Session, lang: LangParam = "en") -> ShareReceipt:
    """With consent only: the idea joins this browser session's demo review queue, or real storage when it is on.
    Either way nothing is sent to A'Pelago."""
    if not body.consent:
        raise HTTPException(status_code=422, detail="Sharing needs your consent: tick the box first.")
    if body.consent_text_version != CONSENT_TEXT_VERSION:
        raise HTTPException(status_code=409, detail="The consent text has changed: reload the form and read it again.")
    model, note = vet.model_for(body.submission.ai_read)
    # Read again here: a tier sent by the browser is never trusted.
    assessment = vet.vet(_checked(body.submission), model=model, reader_note=note)
    consent = ShareConsent(
        given=True,
        scope=["idea", "readiness_read"],
        consent_text_version=CONSENT_TEXT_VERSION,
        given_at=datetime.now(timezone.utc),
    )
    idea = store.SharedIdea(
        submission=body.submission, assessment=assessment.model_copy(update={"stored": True}), consent=consent
    )
    _shared.add(sid, idea)
    path = store.persist_path()
    if path:
        store.persist(idea, path)
    return localize(
        ShareReceipt(
            demo=path is None,
            stored="file" if path else "session_memory",
            expires_at=None if path else datetime.now(timezone.utc) + timedelta(seconds=store.TTL_S),
            item_id=f"session:{assessment.id}",
            consent=consent,
            message=FILE_SHARE_NOTE if path else SESSION_SHARE_NOTE,
        ),
        lang,
    )


@router.get("/shared")
def session_shares(sid: Session) -> SessionShares:
    """Whether this browser session still has shared ideas, so Withdraw stays reachable after a reload."""
    left = _shared.seconds_left(sid)
    if left is None:
        return SessionShares(count=0)
    path_kept = store.persist_path() is not None
    return SessionShares(
        count=len(_shared.ideas(sid)),
        expires_at=None if path_kept else datetime.now(timezone.utc) + timedelta(seconds=left),
    )


@router.post("/withdraw")
def withdraw(sid: Session, lang: LangParam = "en") -> WithdrawReceipt:
    """Withdraws consent: every idea this session shared leaves the queue at once."""
    removed = _shared.forget(sid)
    return localize(
        WithdrawReceipt(
            removed=removed,
            message=f"Withdrawn: {removed} idea(s) removed from the demo review queue."
            if removed
            else "Nothing from this session is in the demo review queue.",
        ),
        lang,
    )


@router.get("/queue")
def review_queue(
    preset: PresetParam,
    mode: ModeParam = "apelago",
    top_n: Annotated[int, Query(ge=1, le=queue_mod.MAX_TOP_N)] = queue_mod.DEFAULT_TOP_N,
    sample: Annotated[bool, Query(description="The sample-data preview, not the live queue.")] = False,
    sid: str | None = Depends(optional_session_id),
    lang: LangParam = "en",
) -> IdeaQueue:
    today = settings().today
    if sample:
        return _localized(queue_mod.build_sample_queue(mode, preset, today=today, top_n=top_n), lang)
    shared = [i for i in _shared.ideas(sid) if i.submission.preset == preset]
    return _localized(queue_mod.build_queue(mode, preset, shared, today=today, top_n=top_n), lang)
