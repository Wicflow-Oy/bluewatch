"""What the ecosystem actor and the startup should do next, in order.

Order: when the company is not yet matched to its register record for certain, "confirm the match" comes
first (no contact goes to a company we may have mixed up); then good-fit items with a deadline in the next
60 days, soonest first; then, when the evidence is thin, "ask the company" (the gaps are the next
investigation step); then everything else by fit, programmes and buyers before grants and investors.
Candidates come from funding opportunities, bridges and investor matches. A company with thin evidence
gets programmes before investors, and a service business gets no investor steps at all. A company past
the stage window gets no steps (nothing here is a lead for it), and a company already in a programme family
is not pointed back to it as a new step.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from bluewatch.config import settings
from bluewatch.models import Assessment, Bridge, Company, InvestorMatch, NextStep, Opportunity
from bluewatch.rules.presets import load_preset

GOOD_TIERS = frozenset({"certain", "likely"})
BRIDGE_FIT = {"verified": 1.0, "probable": 0.75, "possible": 0.5}
TIER_FIT = {"certain": 1.0, "likely": 0.8, "possible": 0.5}
BRIDGE_KIND = {
    "won_before_open_again": "buyer",
    "law_creates_buyer": "buyer",
    "already_works_with": "partner",
    "proof_step": "pilot",
    "lab_window": "programme",
    "programme_fit": "programme",
    "rule_decides": "grant",
}
AUDIENCE = {
    "programme": "both",
    "grant": "startup",
    "pilot": "startup",
    "investor": "startup",
    "buyer": "both",
    "partner": "both",
    "ask_company": "ecosystem_actor",
    "confirm_match": "ecosystem_actor",
}
TIERED_KINDS = frozenset({"programme", "grant", "pilot"})
KIND_ORDER = {"programme": 0, "buyer": 1, "partner": 2, "pilot": 3, "grant": 4, "investor": 5, "ask_company": 6}
DEADLINE_HORIZON_DAYS = 60
MAX_STEPS = 8
THIN_EVIDENCE_INVESTOR_FIT = 0.45  # below any programme or themed call
# A tag that says the company already takes part in an organisation's programmes, and how its titles start.
ALREADY_IN = {"apelago_cohort": "A'Pelago"}


@dataclass
class _Candidate:
    step_id: str
    kind: str
    title: str
    action: str
    why: str
    deadline: date | None
    fit: float


def order(
    company: Company,
    assessment: Assessment,
    opportunities: list[Opportunity],
    investor_matches: list[InvestorMatch],
    bridges: list[Bridge],
    *,
    today: date | None = None,
) -> list[NextStep]:
    if "too_late" in assessment.flags:
        return []
    today = today or settings().today
    thin = assessment.score.evidence < load_preset(assessment.preset).thresholds.solid_evidence
    service = "no_technology_readiness" in assessment.flags
    # Bridges first, so a bridge's sharper action wins when it and an opportunity name the same call.
    candidates = _from_bridges(bridges, opportunities) + _from_opportunities(opportunities, today)
    if not service:
        candidates += _from_investors(investor_matches, thin)
    if thin:
        candidates.append(_ask_company(company, assessment))
    candidates = _not_already_in(company, candidates, opportunities)

    def urgent(c: _Candidate) -> bool:
        return c.deadline is not None and 0 <= (c.deadline - today).days <= DEADLINE_HORIZON_DAYS and c.fit >= 0.75

    def sort_key(c: _Candidate) -> tuple:
        bucket = 0 if urgent(c) else 1 if c.kind == "ask_company" else 2
        if bucket == 0:
            return bucket, c.deadline, 0.0, 0, c.step_id
        return bucket, date.max, -c.fit, KIND_ORDER[c.kind], c.deadline or date.max, c.step_id

    ranked = sorted(_dedupe(candidates), key=sort_key)
    if company.resolution.state != "resolved":
        ranked.insert(0, _confirm_match(company))
    ranked = ranked[:MAX_STEPS]
    return [
        NextStep(
            rank=i + 1,
            opportunity_id=c.step_id,
            kind=c.kind,
            title=c.title,
            action=c.action,
            why=c.why,
            deadline=c.deadline,
            audience=AUDIENCE[c.kind],
        )
        for i, c in enumerate(ranked)
    ]


def _from_opportunities(opportunities: list[Opportunity], today: date) -> list[_Candidate]:
    """Certain and likely items always; a possible one only as a programme, or as a call themed for this
    company with a near deadline, so open-to-anyone and stage-gated calls do not crowd out real steps.
    A generic theme counts for less than one written for the company's field."""

    def worth_a_step(o: Opportunity) -> bool:
        if o.tier in GOOD_TIERS:
            return True
        near = o.deadline is not None and 0 <= (o.deadline - today).days <= DEADLINE_HORIZON_DAYS
        themed = o.priority_parts.get("theme", 0.0) >= 1.0
        return o.tier == "possible" and (o.kind == "programme" or (near and themed))

    return [
        _Candidate(
            o.id,
            o.kind,
            o.title,
            o.action,
            o.rule or "",
            o.deadline,
            round(TIER_FIT[o.tier] * (0.8 + 0.2 * o.priority_parts.get("theme", 1.0)), 3),
        )
        for o in opportunities
        if worth_a_step(o)
    ]


def _from_bridges(bridges: list[Bridge], opportunities: list[Opportunity]) -> list[_Candidate]:
    """A bridge to a call the card also lists as an opportunity (by its rule page, else by name) takes that
    opportunity's id, so the step carries the call's funding tier."""

    def step_id(b: Bridge) -> str:
        if BRIDGE_KIND[b.type] not in TIERED_KINDS:
            return b.id
        pages = {e.url for e in b.evidence_counterparty if e.url}
        listed = next((o for o in opportunities if o.rule_source in pages), None) or next(
            (o for o in opportunities if _same_call(o.title, b.counterparty.name)), None
        )
        return listed.id if listed else b.id

    return [
        _Candidate(
            step_id(b),
            BRIDGE_KIND[b.type],
            b.counterparty.name,
            b.action,
            b.reason,
            b.deadline,
            BRIDGE_FIT[b.confidence],
        )
        for b in bridges
    ]


def _from_investors(matches: list[InvestorMatch], thin: bool) -> list[_Candidate]:
    now = [m for m in matches if m.when == "now"][:2]
    return [
        _Candidate(
            f"investor:{m.investor_id}",
            "investor",
            m.name,
            f"Shortlist {m.name} for the next round",
            m.fit_label,
            None,
            min(THIN_EVIDENCE_INVESTOR_FIT if thin else 1.0, m.score),
        )
        for m in now
    ]


def _ask_company(company: Company, assessment: Assessment) -> _Candidate:
    unknown = [d.key.replace("_", " ") for d in assessment.dimensions if d.state == "unknown"]
    return _Candidate(
        f"ask_company:{company.id}",
        "ask_company",
        "Ask the company to close the biggest gaps",
        "Send an evidence request: one useful opportunity plus the two questions that close the biggest gaps",
        f"The evidence is thin; unknown: {', '.join(unknown[:4]) or 'none'}",
        None,
        0.9,
    )


def _confirm_match(company: Company) -> _Candidate:
    """The outreach desk refuses a company that is not matched for certain, so the match is the first step."""
    reg = company.registry
    if reg.id:
        where = company.domain or "the company's own site"
        action = f"Confirm the match before any contact: check that {where} shows business ID {reg.id}"
    else:
        action = "Find the company's business ID in its national register before any contact"
    return _Candidate(
        f"confirm_match:{company.id}",
        "confirm_match",
        "Confirm the match",
        action,
        company.resolution.reason,
        None,
        1.0,
    )


def _not_already_in(
    company: Company, candidates: list[_Candidate], opportunities: list[Opportunity]
) -> list[_Candidate]:
    """Drops steps back into a programme family the company is already part of: a relationship, not a lead.
    A bridge to such a programme carries the programme's opportunity id, so it goes too."""
    orgs = [org for tag, org in ALREADY_IN.items() if tag in company.tags]
    if not orgs:
        return candidates
    own = {o.id for o in opportunities if any(org in o.title for org in orgs)}
    return [c for c in candidates if c.step_id not in own and not any(org in c.title for org in orgs)]


def _same_call(a: str, b: str) -> bool:
    """Whether two titles name one call, as "Northern Blue 2027" and "Northern Blue 2027 (accelerator)" do."""
    ka, kb = (title.split(" (")[0].strip().lower() for title in (a, b))
    return ka == kb or ka.startswith(kb + " ") or kb.startswith(ka + " ")


def _dedupe(candidates: list[_Candidate]) -> list[_Candidate]:
    """A bridge and an opportunity can name the same call; keep the first one."""
    out: list[_Candidate] = []
    for c in candidates:
        if not any(c.step_id == k.step_id or _same_call(c.title, k.title) for k in out):
            out.append(c)
    return out
