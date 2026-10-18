"""Funding tiers from grants.json: certain / likely / possible / excluded / unknown.

- certain: every deciding rule passes and every one was read on the official page (read or sedia);
- likely: no rule fails and the read rules pass, but something is still unknown;
- possible: the theme fits but a rule comes from a search summary, an inference or the funder's own
  rules, or criteria are not published, or no call is open now;
- excluded: a rule fails (the failing rule is shown, with how sure we are of it);
- unknown: nothing about the instrument could be verified.
Every tier carries the deciding rule, its source and the deadline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from bluewatch import seed
from bluewatch.models import Assessment, Company, FounderTier, Mode, Opportunity, Tier
from bluewatch.rules.eligibility import (
    VERIFIED,
    Applicant,
    Check,
    applicant_from_company,
    check_instrument,
)
from bluewatch.rules.fit import past_window
from bluewatch.rules.presets import load_preset
from bluewatch.rules.text import humanise_keys, parse_date
from bluewatch.rules.topics import is_generic, shared_topics, topics_of

OPEN_STATUSES = frozenset({"open", "continuous", "rolling", "open_no_date"})
TIER_RANK: dict[str, int] = {"certain": 4, "likely": 3, "possible": 2, "unknown": 1, "excluded": 0}
TIER_VALUE = {"certain": 1.0, "likely": 0.8, "possible": 0.5, "unknown": 0.2, "excluded": 0.0}
PROGRAMME_TYPES = frozenset({"accelerator", "coaching", "event", "coalition"})
MAX_UNKNOWNS_FOR_LIKELY = 2
PRIORITY_WEIGHTS = {"tier": 0.4, "deadline": 0.25, "theme": 0.2, "mode_fit": 0.15}


@dataclass(frozen=True)
class Evaluation:
    inst: dict
    tier: Tier
    deciding_rule: str
    rule_verified: bool
    deadline: date | None
    upgrade_path: str | None
    unknown_reason: str | None
    checks: list[Check]


def instruments() -> list[dict]:
    grants = seed.load("grants")
    return grants["instruments"] + grants["eu_topics"]


def evaluate(inst: dict, a: Applicant, today: date) -> Evaluation:
    checks = check_instrument(inst, a)
    deadline = parse_date(inst.get("deadline"))
    status = inst.get("status", "unknown")
    closed = status not in OPEN_STATUSES or (deadline is not None and deadline < today)
    fails = [c for c in checks if c.outcome == "fail"]
    unknowns = [c for c in checks if c.outcome == "unknown"]
    unverified = [c for c in checks if c.tag not in VERIFIED]
    capped = [c for c in checks if c.cap]
    upgrade = next((c.upgrade for c in fails + unknowns + capped if c.upgrade), None)
    reason = None

    if fails:
        # Show a verified failing rule first: it is the stronger statement.
        deciding = sorted(fails, key=lambda c: c.tag not in VERIFIED)[0]
        tier, rule, verified = "excluded", f"{deciding.name}: {deciding.text}", deciding.tag in VERIFIED
    elif status == "unknown" and not any(c.outcome == "pass" and c.tag in VERIFIED for c in checks):
        tier, rule, verified = "unknown", "Nothing about this instrument could be verified", False
        reason = inst.get("deadline_note") or "Status, dates and eligibility not verified"
    elif not checks:
        tier, rule, verified = "possible", "Criteria not published; ask the funder", False
    elif all(c.name == "Theme" for c in checks):
        # A matching theme says nothing about who may apply.
        tier, rule, verified = "possible", "The theme fits; eligibility is not published as rules", False
    elif unknowns:
        first = sorted(unknowns, key=lambda c: c.tag in VERIFIED)[0]
        # "Likely" means one or two open questions; more than that is only "possible".
        tier = "likely" if not unverified and len(unknowns) <= MAX_UNKNOWNS_FOR_LIKELY else "possible"
        rule, verified, reason = f"No rule fails; still unknown: {first.name}: {first.text}", False, first.text
    elif capped or unverified:
        deciding = (capped or unverified)[0]
        # How sure the rule is shows beside it (rule_verified); the text stays the rule itself.
        tier, rule, verified = "possible", f"{deciding.name}: {deciding.text}", False
    else:
        tier, verified = "certain", True
        rule = f"All {len(checks)} hard rules pass, each read on the official page"

    if capped and TIER_RANK[tier] > TIER_RANK["possible"]:
        tier = "possible"
    if closed and TIER_RANK[tier] > TIER_RANK["possible"]:
        tier = "possible"
        rule += f"; no open call now ({humanise_keys(status)})"
    return Evaluation(inst, tier, rule, verified, deadline, upgrade, reason, checks)


def tiers_for(a: Applicant, *, today: date) -> list[FounderTier]:
    """Every instrument and EU topic, tiered for one applicant (pure: no storage, no network). The founder
    view and the funding page build the same applicant for the same company, so they give one verdict."""
    evaluations = [evaluate(inst, a, today) for inst in instruments()]
    evaluations.sort(key=lambda e: (-TIER_RANK[e.tier], e.deadline or date.max, e.inst["name"]))
    return [
        FounderTier(
            instrument_id=e.inst["id"],
            instrument_name=e.inst["name"],
            tier=e.tier,
            deciding_rule=e.deciding_rule,
            rule_source=e.inst.get("url"),
            rule_verified=e.rule_verified,
            deadline=e.deadline,
            upgrade_path=e.upgrade_path,
            unknown_reason=e.unknown_reason,
        )
        for e in evaluations
    ]


def funding_opportunities(
    company: Company, assessment: Assessment, *, mode: Mode, today: date, limit: int = 12
) -> list[Opportunity]:
    """Grants, programmes and proof steps for one company, best first; excluded ones are left out. For a
    company past the stage window none of them applies: each says so, with the gate it met."""
    a = applicant_from_company(company, assessment.levels, today)
    preset = load_preset(assessment.preset)
    out = []
    for inst in instruments():
        e = evaluate(inst, a, today)
        if e.tier == "excluded" or (inst["type"] == "access_programme" and not _proof_step_fits(inst, a)):
            continue
        out.append(
            opportunity(company.id, e, a, mode, today, inst["id"] in preset.programmes, frozenset(preset.grant_topics))
        )
    out.sort(key=lambda o: (-o.priority, o.id))
    late = past_window(assessment)
    return [_not_applicable(o, late) for o in out[:limit]] if late else out[:limit]


def _not_applicable(o: Opportunity, rule: str) -> Opportunity:
    """An instrument a company past the stage window is not pointed to: whatever the funder's own rules say,
    the window decides, so it carries that rule and no action or upgrade."""
    return o.model_copy(
        update={
            "tier": "excluded",
            "rule": rule,
            "rule_source": None,
            "rule_verified": False,
            "upgrade_path": None,
            "action": "Not applicable: the company is past the stage window",
        }
    )


def opportunity(
    company_id: str,
    e: Evaluation,
    a: Applicant,
    mode: Mode,
    today: date,
    preset_programme: bool,
    preset_topics: frozenset[str],
) -> Opportunity:
    inst = e.inst
    kind = kind_of(inst, preset_programme)
    themes = "; ".join(inst.get("themes") or [])
    parts = {
        "tier": TIER_VALUE[e.tier],
        "deadline": _urgency(e.deadline, inst.get("status"), today),
        "theme": 1.0 if shared_topics(themes, preset_topics) else 0.5 if is_generic(themes) else 0.3,
        "mode_fit": 1.0 if (kind != "grant") == (mode == "apelago") else 0.5,
    }
    weighted = {k: round(PRIORITY_WEIGHTS[k] * v, 4) for k, v in parts.items()}
    return Opportunity(
        id=f"{company_id}:{inst['id']}",
        company_id=company_id,
        kind=kind,
        ref_id=inst["id"],
        title=inst["name"],
        tier=e.tier,
        rule=e.deciding_rule,
        rule_source=inst.get("url"),
        rule_verified=e.rule_verified,
        deadline=None if _two_stage(inst) else e.deadline,
        upgrade_path=e.upgrade_path,
        evidence_ids=list(a.evidence_ids),
        why=_why(e),
        action=_action(kind, e, inst),
        priority=round(sum(weighted.values()), 4),
        priority_parts=weighted,
    )


def kind_of(inst: dict, preset_programme: bool = False) -> str:
    if inst["type"] == "access_programme":
        return "pilot"
    return "programme" if inst["type"] in PROGRAMME_TYPES or preset_programme else "grant"


def _proof_step_fits(inst: dict, a: Applicant) -> bool:
    """A validation step (test facility, observatory) needs a technology of its kind to validate: the
    company must share a specific topic with it, not just the broad blue-economy umbrella."""
    specific = topics_of("; ".join(inst.get("themes") or [])) - {"ocean"}
    return a.trl_applicable and bool(specific & a.topics)


def _urgency(deadline: date | None, status: str | None, today: date) -> float:
    if deadline is None:
        return 0.4 if status in ("continuous", "rolling") else 0.2
    days = (deadline - today).days
    return 1.0 if days <= 14 else 0.8 if days <= 30 else 0.5 if days <= 60 else 0.3


def _why(e: Evaluation) -> list[str]:
    lines = [f"{c.outcome.capitalize()}: {c.name}: {c.text} ({c.tag})" for c in e.checks]
    for note_field in ("deadline_note", "amount_note"):
        if e.inst.get(note_field):
            lines.append(humanise_keys(str(e.inst[note_field])))
    return lines


def _two_stage(inst: dict) -> bool:
    """A call where the first step (a short proposal) is open any time and the dated cut-off is only
    for invited full proposals (EIC Accelerator): the date is not an apply-by date for a newcomer."""
    return "short proposals any time" in str(inst.get("deadline_note", "")).lower()


def _action(kind: str, e: Evaluation, inst: dict) -> str:
    when = f" by {e.deadline:%d %b %Y}" if e.deadline else ""
    if _two_stage(inst):
        cutoff = f"; the next full-proposal cut-off is {e.deadline:%d %b %Y}" if e.deadline else ""
        return f"Submit a short proposal first (any time){cutoff}"
    if kind == "pilot":
        return f"Send a letter of intent to a facility{when}"
    if kind == "programme":
        return f"Invite the company to apply to {inst['name']}{when}"
    if e.tier in ("certain", "likely"):
        return f"Apply{when}" if when else "Apply (open on a rolling basis)"
    return f"Check eligibility with {inst.get('funder', 'the funder')}{when}"
