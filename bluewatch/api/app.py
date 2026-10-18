"""BlueWatch HTTP API (FastAPI) and the built front end, in one process.

- No login. No keys ever reach the browser.
- Every response carries X-Robots-Tag: noindex; /robots.txt disallows everything.
- The live lookup and founder view are rate-limited per IP and never store, log or forward what a
  visitor enters (POST bodies, so IDs stay out of URLs; no access log in the container).

Run locally: uvicorn bluewatch.api.app:app --port 8787
"""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Literal, ParamSpec, TypeVar

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel

from bluewatch import demo, labels, lookup
from bluewatch.api import ideas
from bluewatch.api.deps import ModeParam, PresetParam, preset_param, rate_check, read_capped
from bluewatch.api.sessions import DeskSessions
from bluewatch.config import FRONTEND_DIST, settings
from bluewatch.i18n import Lang, LangParam, localize, localize_text
from bluewatch.models import (
    CONTRACTS_VERSION,
    Alert,
    AuditEvent,
    Bridge,
    CompanyRow,
    ContactPlan,
    DeskDraft,
    DeskReply,
    FundingCatalogue,
    OutreachDraft,
    PrecisionReport,
    PresetInfo,
    ShortList,
    SourceStatus,
    VentureCard,
)
from bluewatch.outreach.desk import Desk, DeskError
from bluewatch.outreach.drafts import DraftRefused, evidence_request, text_hash
from bluewatch.read import live as site_reader
from bluewatch.sources import search


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # In the background, so /api/health answers at once and the first visitor of each day finds lists and
    # cards ready.
    stop = threading.Event()
    threading.Thread(target=demo.keep_warm, args=(stop,), name="warm-caches", daemon=True).start()
    yield
    stop.set()


app = FastAPI(title=f"{labels.PRODUCT_NAME} API", version="0.1.0", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1024)  # the funding catalogue is ~600 KB of JSON
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(ideas.router)  # Idea Harbour: /api/ideas/*

BLIND_MAX_BYTES = 200_000
DEMO_APPROVER = "demo reviewer"  # the visitor's own name is never asked for or stored
_desks = DeskSessions()
P = ParamSpec("P")
R = TypeVar("R")

CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


@app.middleware("http")
async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    response = await call_next(request)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = CSP
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _known(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    """Call a precomputed lookup; a company ID outside the precomputed set is a 404."""
    try:
        return fn(*args, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Not found in the precomputed set.") from exc


@app.get("/robots.txt", include_in_schema=False)
def robots() -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/meta")
def meta(lang: LangParam = "en") -> dict:
    s = settings()
    return localize(
        {
            "product_name": labels.PRODUCT_NAME,
            "list_name": labels.LIST_NAME,
            "modes": ["apelago", "redstone"],
            "today": s.today.isoformat(),
            "outreach_mode": s.outreach_mode,
            "public_mode": s.public_mode,
            "live_lookups": s.live_lookups,
            "contracts_version": CONTRACTS_VERSION,
            "group_labels": labels.GROUP_LABELS,
            "group_rule": labels.GROUP_RULE,
            "tier_labels": labels.TIER_LABELS,
            "level_labels": labels.LEVEL_LABELS,
            "dimension_labels": labels.DIMENSION_LABELS,
            "attribution": labels.ATTRIBUTION,
            "live_reader": site_reader.enabled(),
            "build": s.build,
        },
        lang,
    )


@app.get("/api/sources")
def sources(lang: LangParam = "en") -> list[SourceStatus]:
    return localize(demo.demo_sources(), lang)


@app.get("/api/presets")
def presets(lang: LangParam = "en") -> list[PresetInfo]:
    return localize(demo.presets(), lang)


@app.get("/api/list")
def shortlist(preset: PresetParam, mode: ModeParam = "apelago", lang: LangParam = "en") -> ShortList:
    return localize(_known(demo.shortlist, mode, preset), lang)


@app.get("/api/companies")
def companies(preset: PresetParam, mode: ModeParam = "apelago", lang: LangParam = "en") -> list[CompanyRow]:
    return localize(_known(demo.companies, mode, preset), lang)


@app.get("/api/companies/{company_id}")
def venture_card(
    company_id: str, preset: PresetParam, mode: ModeParam = "apelago", lang: LangParam = "en"
) -> VentureCard:
    return localize(_known(demo.venture_card, company_id, mode, preset), lang)


@app.get("/api/bridges")
def bridges(mode: ModeParam = "apelago", lang: LangParam = "en") -> list[Bridge]:
    return localize(demo.bridges(mode), lang)


@app.get("/api/bridges/{bridge_id:path}")
def bridge(bridge_id: str, mode: ModeParam = "apelago", lang: LangParam = "en") -> Bridge:
    found = next((b for b in demo.bridges(mode) if b.id == bridge_id), None)
    if found is None:
        raise HTTPException(status_code=404, detail="No live bridge with this ID in this workspace.")
    return localize(found, lang)


@app.get("/api/funding")
def funding(mode: ModeParam = "apelago", lang: LangParam = "en") -> FundingCatalogue:
    return localize(demo.funding(mode), lang)


@app.get("/api/alerts")
def alerts(mode: ModeParam = "apelago", lang: LangParam = "en") -> list[Alert]:
    return localize(demo.alerts(mode), lang)


@app.get("/api/precision")
def precision(lang: LangParam = "en") -> PrecisionReport:
    return localize(demo.precision(), lang)


@app.post("/api/precision/blind")
async def precision_blind(request: Request, lang: LangParam = "en") -> PrecisionReport:
    """A partner's blind set (CSV, or JSON with Content-Type application/json), scored in memory only:
    the upload is never written to disk, logged or kept after the response."""
    rate_check(request)
    raw = await read_capped(request, BLIND_MAX_BYTES, "The blind set is limited to 200 KB.")
    try:
        text = raw.decode("utf-8")
        report = demo.blind_precision(text, json_format="json" in request.headers.get("content-type", ""))
    except (UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not read the file: send UTF-8 CSV with a company or id column, or JSON in the same shape.",
        ) from exc
    return localize(report, lang)


@app.get("/api/scout")
def scout(top_n: int = 20, mode: ModeParam = "apelago", lang: LangParam = "en") -> list[ContactPlan]:
    """Contact plans for pre-company teams, each with its project as the organiser published it (never the
    project's internal research notes) and the workspace's own offer."""
    return localize(_known(demo.scout_plans, top_n, mode), lang)


class LookupRequest(BaseModel):
    country: Literal["FI", "NO", "EE"]
    business_id: str


@app.post("/api/lookup")
def live_lookup(body: LookupRequest, request: Request, lang: LangParam = "en"):
    rate_check(request)
    try:
        return localize(lookup.lookup(body.country, body.business_id), lang)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/founder")
def founder_view(body: LookupRequest, request: Request, lang: LangParam = "en"):
    """The founder view for any business ID: register facts plus the same rules, flipped."""
    rate_check(request)
    try:
        found = lookup.lookup(body.country, body.business_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if found.natural_person or found.registry is None:
        return localize({"lookup": found, "view": None}, lang)
    from bluewatch.founder import view as view_mod

    profile = view_mod.profile_from_registry(found.registry)
    # A company that already has a card is tiered on its researched facts, the same as its card.
    data = demo.build()
    cid = found.company_id
    researched = (data.companies[cid], data.assessments[cid]) if cid in data.companies else None
    view = view_mod.evaluate(profile, settings().today, registry=found.registry, researched=researched)
    return localize({"lookup": found, "view": view}, lang)


class CardRequest(LookupRequest):
    mode: ModeParam = "apelago"
    preset: str = "blue"


def _card_lookup(body: CardRequest, request: Request) -> tuple[lookup.LookupResult, str]:
    rate_check(request)
    preset = preset_param(body.preset)
    try:
        return lookup.lookup(body.country, body.business_id), preset
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _register_only(found: lookup.LookupResult) -> bool:
    """A company outside the precomputed set that the register knows: the one case with a live card."""
    return found.company_id is None and not found.natural_person and found.registry is not None


@app.post("/api/lookup/card")
def live_card(body: CardRequest, request: Request, lang: LangParam = "en"):
    """Any business ID as a venture card: register facts plus the same rules, at once. Nothing is stored or
    logged; a sole trader gets no card. The company's website is read separately (/api/lookup/card/read)."""
    found, preset = _card_lookup(body, request)
    if found.company_id:
        card = demo.venture_card(found.company_id, body.mode, preset)
    elif _register_only(found):
        card = demo.live_card(found.registry, body.mode, preset)
    else:
        card = None
    return localize({"lookup": found, "card": card}, lang)


@app.post("/api/lookup/card/read")
def live_card_read(body: CardRequest, request: Request, lang: LangParam = "en"):
    """The live card again, with the company's own website read and its quote-checked claims added. `read`
    says how the read went; it is null for a company that has no live card. Nothing is stored or logged."""
    found, preset = _card_lookup(body, request)
    if not _register_only(found):
        return localize({"lookup": found, "card": None, "read": None}, lang)
    company, _ = demo.live_company(found.registry)
    site = site_reader.read_site(company)
    card = demo.live_card(found.registry, body.mode, preset, site)
    return localize({"lookup": found, "card": card, "read": site.status}, lang)


class SearchRequest(BaseModel):
    query: str
    country: search.SearchCountry | None = None


@app.post("/api/search")
def name_search(body: SearchRequest, request: Request, lang: LangParam = "en") -> search.SearchResult:
    """Any company by name, in the registers (live when BLUEWATCH_LIVE_LOOKUPS=1, else the recorded data) and the
    precomputed set. The name goes only to the registers; it is never stored or logged, and sole traders never
    appear."""
    rate_check(request)
    try:
        return localize(search.search(body.query, body.country), lang)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# --- the outreach desk (demo): one in-memory desk per visitor; nothing is ever e-mailed
def session_desk(x_demo_session: str = Header(...)) -> Desk:
    try:
        return _desks.desk(x_demo_session)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


SessionDesk = Annotated[Desk, Depends(session_desk)]


def _view(desk: Desk, draft: OutreachDraft, lang: Lang) -> DeskDraft:
    """The draft as written (its text keeps the draft's own language), with the policy's reasons and the
    audit trail's details in `lang`. The hash is of the draft as written."""
    shown = draft.model_copy(update={"audit": [_audit_event(event, lang) for event in draft.audit]})
    return DeskDraft(draft=shown, text_hash=text_hash(draft), decision=localize(desk.decision(draft.id), lang))


def _audit_event(event: AuditEvent, lang: Lang) -> AuditEvent:
    """An audit event with each policy reason in its detail ("route x; reason; reason") in `lang`."""
    detail = "; ".join(localize_text(part, lang) for part in event.detail.split("; "))
    return event.model_copy(update={"detail": detail})


def _desk_call(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    """Call the desk; a step the desk refuses is a 409 with its reason."""
    try:
        return fn(*args, **kwargs)
    except DeskError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


class DraftRequest(BaseModel):
    company_id: str
    mode: ModeParam = "apelago"
    language: Literal["en", "fi", "sv"] = "en"
    bridge_id: str | None = None  # the bridge the draft was started from; else the company's best offer


class ApproveRequest(BaseModel):
    text_hash: str


@app.get("/api/outreach/drafts")
def outreach_drafts(desk: SessionDesk, lang: LangParam = "en") -> list[DeskDraft]:
    return [_view(desk, d, lang) for d in desk.drafts()]


@app.post("/api/outreach/drafts")
def outreach_create(body: DraftRequest, desk: SessionDesk, lang: LangParam = "en") -> DeskDraft:
    """An evidence request for a precomputed company: the bridge it was started from, else its best bridge or
    opportunity, plus the two questions that close its biggest gaps, queued for approval."""
    card = _known(demo.venture_card, body.company_id, body.mode)
    offers = [*card.bridges, *(o for o in card.opportunities if o.tier != "excluded" and o.kind != "ask_company")]
    if body.bridge_id is not None:
        offers = [b for b in card.bridges if b.id == body.bridge_id]
        if not offers:
            raise HTTPException(
                status_code=422, detail=localize_text("That bridge is not one of this company's current bridges.", lang)
            )
    ledger = card.ledger
    try:
        draft = evidence_request(
            card.company, ledger, offers[0] if offers else None, language=body.language, workspace=body.mode
        )
    except DraftRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    evidence = ledger.facts + ledger.assumptions + ledger.unknowns
    return _view(desk, _desk_call(desk.submit, draft, company=card.company, evidence=evidence), lang)


@app.get("/api/outreach/drafts/{draft_id}")
def outreach_draft(draft_id: str, desk: SessionDesk, lang: LangParam = "en") -> DeskDraft:
    return _view(desk, _desk_call(desk.get, draft_id), lang)


@app.post("/api/outreach/drafts/{draft_id}/approve")
def outreach_approve(draft_id: str, body: ApproveRequest, desk: SessionDesk, lang: LangParam = "en") -> DeskDraft:
    return _view(desk, _desk_call(desk.approve, draft_id, DEMO_APPROVER, body.text_hash), lang)


@app.post("/api/outreach/drafts/{draft_id}/send")
def outreach_send(draft_id: str, desk: SessionDesk, lang: LangParam = "en") -> DeskDraft:
    """The demo send: the desk runs in public mode, so the draft ends as blocked_demo and nothing leaves."""
    return _view(desk, _desk_call(desk.send, draft_id), lang)


@app.post("/api/outreach/drafts/{draft_id}/reply")
def outreach_reply(draft_id: str, desk: SessionDesk, lang: LangParam = "en") -> DeskReply:
    """A simulated company reply: each question gets a fixed example answer, marked as simulated."""
    reply, confirmed = _desk_call(desk.simulate_reply, draft_id, _desk_call(desk.simulated_answers, draft_id))
    return DeskReply(draft=_view(desk, desk.get(draft_id), lang), reply=reply, confirmed=localize(confirmed, lang))


@app.get("/api/outreach/drafts/{draft_id}/audit")
def outreach_audit(draft_id: str, desk: SessionDesk, lang: LangParam = "en") -> list[AuditEvent]:
    _desk_call(desk.get, draft_id)
    return [_audit_event(event, lang) for event in desk.audit_log(draft_id)]


@app.post("/api/outreach/reset")
def outreach_reset(x_demo_session: str = Header(...)) -> dict:
    _desks.reset(x_demo_session)
    return {"reset": True}


@app.post("/api/founder/share")
def founder_share(lang: LangParam = "en"):
    """Sharing is off: nothing is stored or sent. With sharing on, this records consent and notifies A'Pelago."""
    return localize(
        {
            "demo": True,
            "stored": False,
            "message": "Sharing is off in this workspace, so A'Pelago didn't receive this profile. "
            "Nothing was stored or sent.",
            "at": datetime.now(timezone.utc).isoformat(),
        },
        lang,
    )


# --- the built front end (single-page app), served last so /api routes win
IMMUTABLE = "public, max-age=31536000, immutable"


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Unknown API route.")
    if not FRONTEND_DIST.exists():
        raise HTTPException(status_code=404, detail="Front end not built.")
    target = (FRONTEND_DIST / path).resolve()
    if path and target.is_file() and FRONTEND_DIST.resolve() in target.parents:
        # Built chunks carry a content hash in their name, so they never change under the same URL.
        immutable = path.startswith("assets/")
        return FileResponse(target, headers={"Cache-Control": IMMUTABLE if immutable else "no-cache"})
    if path.startswith("assets/"):
        # A chunk from an older build: a 404 lets the page reload, where index.html would fail as a script.
        raise HTTPException(status_code=404, detail="No such file in this build.")
    return FileResponse(FRONTEND_DIST / "index.html", headers={"Cache-Control": "no-cache"})
