"""The demo pipeline: seeds and recorded fixtures → contract objects, computed once per day.

Everything shown in the no-login demo is precomputed from the verified demo pack and recorded
public data, so the demo works offline.
"""

from __future__ import annotations

import inspect
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache, wraps
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from bluewatch.bridges import rank as bridge_rank
from bluewatch.config import HELSINKI, settings
from bluewatch.evals import blind
from bluewatch.evals import precision as precision_mod
from bluewatch.founder import view
from bluewatch.labels import SOURCE_LABELS
from bluewatch.models import (
    Alert,
    Assessment,
    Bridge,
    Company,
    CompanyRow,
    ContactPlan,
    Evidence,
    FundingCatalogue,
    FundingCheck,
    FundingInstrument,
    FundingTierRow,
    Mode,
    PrecisionReport,
    PresetInfo,
    PublishedRule,
    Registry,
    ShortList,
    Signal,
    SourceState,
    SourceStatus,
    VentureCard,
)
from bluewatch.rules import alerts as alerts_mod
from bluewatch.rules import assess as assess_mod
from bluewatch.rules import eligibility, gaps, investors, nextsteps, rank, seed_adapter, version
from bluewatch.rules import funding as funding_mod
from bluewatch.rules import presets as presets_mod
from bluewatch.rules.text import humanise_keys
from bluewatch.scout import plans

if TYPE_CHECKING:
    from bluewatch.read.live import SiteReading

MODES: tuple[Mode, ...] = ("apelago", "redstone")
REGISTERS = {"FI": "prh", "NO": "brreg", "EE": "rik"}  # the evidence source family of each country's register
COUNTRY_NAMES = {"FI": "Finland", "NO": "Norway", "EE": "Estonia", "SE": "Sweden", "DK": "Denmark"}
# Published rule fields in grants.json; deadlines, status and amounts are shown separately.
RULE_FIELDS = (
    "country_rule",
    "consortium_rule",
    "size_rule",
    "age_rule",
    "applicant_types",
    "trl_min",
    "trl_max",
    "other_hard_rules",
)
DIGEST_WEEKDAY, DIGEST_HOUR = 0, 7  # the weekly digest goes out on Mondays at 07:00 Helsinki time
WARM_CHECK_S = 300.0

P = ParamSpec("P")
R = TypeVar("R")


def per_day(fn: Callable[P, R]) -> Callable[P, R]:
    """Cache a precomputed result per day: deadlines, ages and windows are relative to today, so a new day
    recomputes instead of serving yesterday's countdowns. Treat the returned objects as read-only."""
    signature = inspect.signature(fn)
    cached = lru_cache(maxsize=1024)(lambda today, *args: fn(*args))

    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        call = signature.bind(*args, **kwargs)
        call.apply_defaults()  # shortlist("apelago") and shortlist("apelago", "blue") share one entry
        return cached(settings().today, *call.args)

    return wrapper


@dataclass
class DemoData:
    generated_at: datetime
    companies: dict[str, Company] = field(default_factory=dict)
    evidence: dict[str, list[Evidence]] = field(default_factory=dict)
    signals: dict[str, list[Signal]] = field(default_factory=dict)
    assessments: dict[str, Assessment] = field(default_factory=dict)
    sources: list[SourceStatus] = field(default_factory=list)


@per_day
def build(preset: str = "blue") -> DemoData:
    data = DemoData(generated_at=datetime.now(timezone.utc))
    for company, evidence, signals in seed_adapter.demo_items():
        if company.registry.natural_person:
            continue
        data.companies[company.id] = company
        data.evidence[company.id] = evidence
        data.signals[company.id] = signals
        data.assessments[company.id] = assess_mod.assess(company, evidence, preset=preset)
    data.sources = demo_sources()
    return data


def demo_sources() -> list[SourceStatus]:
    """Source status for the demo. Recorded snapshots are labelled as such, never as live, and a source we
    have not loaded is shown as unavailable rather than left out, so its companies are not counted as zero."""
    now = datetime.now(timezone.utc)

    def status(source: str, state: SourceState, detail: str) -> SourceStatus:
        checked = None if state in ("unavailable", "planned") else now
        return SourceStatus(source=source, label=SOURCE_LABELS[source], state=state, checked_at=checked, detail=detail)

    return [
        status("prh", "cached", "recorded snapshot"),
        status("brreg", "cached", "recorded snapshot"),
        status("rik", "daily_file", "daily bulk file"),
        status(
            "scb",
            "planned",
            "not connected yet; Swedish companies come from the research pack only",
        ),
        status("ted", "cached", "recorded snapshot"),
        status("cordis", "cached", "export of 17 Oct"),
    ]


def last_digest(today: date) -> datetime:
    """The most recent weekly digest on or before today (Monday 07:00 in Helsinki)."""
    monday = today - timedelta(days=(today.weekday() - DIGEST_WEEKDAY) % 7)
    return datetime.combine(monday, time(DIGEST_HOUR), tzinfo=HELSINKI)


@per_day
def shortlist(mode: Mode, preset: str = "blue") -> ShortList:
    data = build(preset)
    items = [
        (data.companies[cid], data.assessments[cid], data.evidence[cid], data.signals[cid]) for cid in data.companies
    ]
    short = rank.shortlist(
        items, mode=mode, preset=preset, cap=10, since=last_digest(settings().today), sources=data.sources
    )
    # Each row leads with the same first step its venture card shows, so the list and the card never disagree.
    for entry in short.entries:
        steps = venture_card(entry.company_id, mode, preset).next_steps
        if steps:
            entry.next_action, entry.deadline = steps[0].action, steps[0].deadline
    return short


@per_day
def venture_card(company_id: str, mode: Mode, preset: str = "blue") -> VentureCard:
    data = build(preset)
    if company_id not in data.companies:
        raise KeyError(company_id)
    return card_for(
        data.companies[company_id],
        data.evidence[company_id],
        data.assessments[company_id],
        mode=mode,
        preset=preset,
        sources=data.sources,
    )


def card_for(
    company: Company,
    evidence: list[Evidence],
    assessment: Assessment,
    *,
    mode: Mode,
    preset: str,
    sources: list[SourceStatus],
) -> VentureCard:
    card = VentureCard(
        company=company,
        assessment=assessment,
        ledger=gaps.ledger(company, evidence),
        evidence=evidence,
        sources=sources,
    )
    if "closed" in assessment.flags:  # no longer trading: its group rule says so, and nothing is a lead for it
        return card
    today = settings().today
    opportunities = funding_mod.funding_opportunities(company, assessment, mode=mode, today=today)
    matches = investors.match(company, assessment, mode=mode, preset=preset)
    bridges = bridge_rank.for_company(company.id, today=today, limit=3, mode=mode)
    steps = nextsteps.order(company, assessment, opportunities, matches, bridges, today=today)
    return card.model_copy(
        update={"opportunities": opportunities, "investors": matches, "bridges": bridges, "next_steps": steps}
    )


def live_company(registry: Registry) -> tuple[Company, list[Evidence]]:
    """A company outside the precomputed set, from register facts only, each fact cited to its register."""
    profile = view.profile_from_registry(registry)
    company = view.as_company(profile, registry)
    register = REGISTERS.get(registry.country)
    evidence = [
        e.model_copy(update={"source_family": register or e.source_family})
        for e in view.profile_evidence(profile, company)
    ]
    return company, evidence


def live_card(registry: Registry, mode: Mode, preset: str = "blue", site: SiteReading | None = None) -> VentureCard:
    """A card for a company outside the precomputed set: register facts, plus the quote-checked claims from
    its own website when it was read, through the same rules. Everything else stays unknown."""
    company, evidence = live_company(registry)
    if site is not None and site.status.state == "read":
        company = company.model_copy(update={"domain": site.status.host, "vertical": site.vertical})
        evidence = [*evidence, *site.evidence]
    assessment = assess_mod.assess(company, evidence, preset=preset)
    return card_for(company, evidence, assessment, mode=mode, preset=preset, sources=[])


@per_day
def companies(mode: Mode, preset: str = "blue") -> list[CompanyRow]:
    """Every company in the precomputed set, best potential first, each with its card's first step."""
    data = build(preset)
    rows = []
    for cid, company in data.companies.items():
        score = data.assessments[cid].score
        steps = venture_card(cid, mode, preset).next_steps
        rows.append(
            CompanyRow(
                id=cid,
                name=company.names[0],
                country=company.registry.country,
                registry_id=company.registry.id,
                founded=company.registry.founded,
                vertical=company.vertical,
                vertical_note=company.vertical_note,
                tags=company.tags,
                resolution=company.resolution.state,
                group=score.group,
                potential=score.potential,
                evidence=score.evidence,
                next_action=steps[0].action if steps else None,
                deadline=steps[0].deadline if steps else None,
            )
        )
    rows.sort(key=lambda r: (-r.potential, -r.evidence, r.name))
    return rows


def presets() -> list[PresetInfo]:
    return [
        PresetInfo(name=p.name, label=p.label, description=p.description)
        for p in map(presets_mod.load_preset, presets_mod.preset_names())
    ]


@per_day
def bridges(mode: Mode) -> list[Bridge]:
    """Every live bridge for the workspace, best first (deadline x fit x evidence), each with a
    description from register data that stands in for the company when a viewer hides names."""
    today = settings().today
    known = build().companies
    out = []
    for bridge in bridge_rank.all_bridges(today):
        if bridge.mode not in (mode, "both"):
            continue
        parts = bridge_rank.rank_parts(bridge, today)
        if parts["deadline"] > 0:
            out.append(
                bridge.model_copy(update={"rank_parts": parts, "anonymised_name": anonymised_name(bridge, known)})
            )
    out.sort(
        key=lambda b: (-b.rank_parts["score"], b.deadline or date.max, bridge_rank.CONFIDENCE_ORDER[b.confidence], b.id)
    )
    return out


def anonymised_name(bridge: Bridge, known: dict[str, Company]) -> str:
    """The seed's own label when it has one, else place and vertical from the register: never a new fact."""
    if bridge.anonymised_name:
        return bridge.anonymised_name
    party = bridge.company
    company = known.get(party.company_id or "")
    if company is None:
        who = "A research team" if "team" in party.name.lower() else "An organisation"
        where = COUNTRY_NAMES.get(party.country or "")
        return f"{who} in {where}" if where else who
    where = company.registry.municipality or COUNTRY_NAMES.get(company.registry.country)
    vertical = presets_mod.load_preset("blue").verticals.get(company.vertical or "")
    label = "A company" + (f" in {where}" if where else "")
    return f"{label} ({vertical.label.lower()})" if vertical else label


@per_day
def funding(mode: Mode) -> FundingCatalogue:
    """The instrument catalogue, each instrument tiered for this week's shortlisted companies."""
    data = build()
    today = settings().today
    listed = [data.companies[e.company_id] for e in shortlist(mode).entries]
    applicants = [(c, eligibility.applicant_from_company(c, data.assessments[c.id].levels, today)) for c in listed]
    instruments = []
    for inst in funding_mod.instruments():
        tiers = []
        for company, applicant in applicants:
            e = funding_mod.evaluate(inst, applicant, today)
            tiers.append(
                FundingTierRow(
                    company_id=company.id,
                    name=company.names[0],
                    country=company.registry.country,
                    tier=e.tier,
                    deciding_rule=e.deciding_rule,
                    rule_verified=e.rule_verified,
                    upgrade_path=e.upgrade_path,
                    unknown_reason=e.unknown_reason,
                    checks=[
                        FundingCheck(
                            name=c.name,
                            outcome=c.outcome,
                            text=c.text,
                            source_tag=c.tag,
                            verified=c.tag in eligibility.VERIFIED,
                        )
                        for c in e.checks
                    ],
                )
            )
        tiers.sort(key=lambda t: (-funding_mod.TIER_RANK[t.tier], t.name))
        instruments.append(
            FundingInstrument(
                id=inst["id"],
                name=inst["name"],
                funder=inst.get("funder"),
                type=inst["type"],
                kind=funding_mod.kind_of(inst),
                status=inst.get("status", "unknown"),
                deadline=funding_mod.parse_date(inst.get("deadline")),
                deadline_note=inst.get("deadline_note"),
                url=inst.get("url"),
                themes=inst.get("themes") or [],
                rules=_published_rules(inst),
                tiers=tiers,
            )
        )
    best = {i.id: max((funding_mod.TIER_RANK[t.tier] for t in i.tiers), default=0) for i in instruments}
    instruments.sort(key=lambda i: (-best[i.id], i.deadline or date.max, i.name))
    return FundingCatalogue(
        mode=mode,
        today=today,
        rules_version=version.rules_version(),
        company_ids=[c.id for c in listed],
        instruments=instruments,
    )


def _published_rules(inst: dict) -> list[PublishedRule]:
    out = []
    for field_name in RULE_FIELDS:
        value = inst.get(field_name)
        if value in (None, "", []):
            continue
        text = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
        tag = eligibility.tag_of(inst, field_name)
        out.append(
            PublishedRule(
                field=field_name, text=humanise_keys(text), source_tag=tag, verified=tag in eligibility.VERIFIED
            )
        )
    return out


@per_day
def alerts(mode: Mode) -> list[Alert]:
    """Deadline alerts (14 and 30 days) and new signals on this week's listed companies. Share issues are
    founder-sensitive, so A'Pelago mode leaves them out."""
    data = build()
    ids = [e.company_id for e in shortlist(mode).entries]
    signals = [
        s for cid in ids for s in data.signals[cid] if mode == "redstone" or s.sensitivity != "founder_sensitive"
    ]
    opportunities = [o for cid in ids for o in venture_card(cid, mode).opportunities]
    return alerts_mod.alerts(signals, [data.companies[cid] for cid in ids], opportunities, today=settings().today)


@per_day
def precision() -> PrecisionReport:
    """Agreement with the answer keys, the age baseline beside every number, and the entity traps."""
    data = build()
    return precision_mod.report(data.assessments, companies=list(data.companies.values()), today=settings().today)


def blind_precision(text: str, *, json_format: bool) -> PrecisionReport:
    """A partner's blind set, scored in memory: the text is never written anywhere."""
    data = build()
    return blind.score_blind_rows(
        blind.parse_blind_set(text, json_format=json_format),
        name="uploaded blind set",
        assessments=data.assessments,
        companies=list(data.companies.values()),
    )


def scout_plans(top_n: int = 20, mode: Mode = "apelago") -> list[ContactPlan]:
    return plans.plans(top_n=top_n, mode=mode)


def warm() -> None:
    """Precompute every list, card and catalogue in both workspaces and presets, so the first visitor
    does not wait for the rules."""
    for mode in MODES:
        for preset in presets_mod.preset_names():
            shortlist(mode, preset)
            companies(mode, preset)
        bridges(mode)
        funding(mode)
        alerts(mode)
    precision()


def keep_warm(stop: threading.Event, check_every_s: float = WARM_CHECK_S) -> None:
    """Warm now, and again whenever the date changes: the caches are per day, so without this the first
    visitor after midnight would wait for the whole set to be recomputed."""
    warmed = None
    while True:
        today = settings().today
        if today != warmed:
            warm()
            warmed = today
        if stop.wait(check_every_s):
            return
