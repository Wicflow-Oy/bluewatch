"""The parts of potential: thesis fit (from the preset), stage fit (investment readiness and age),
venture type and traction. Each returns a value and a plain note; value None means unknown, and the
score leaves unknown parts out instead of counting them as zero.

The too-late gates close the window on an established company whatever its other evidence says: a
public limited company form, an age past the preset's window, more than 250 employees, or revenue above
EUR 10 million. Each reads a value a register or the company states; an unknown value never closes a gate."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bluewatch.models import Assessment, Company, Evidence, ReadinessLevel
from bluewatch.rules.evidence import facts, field_of, is_self_reported
from bluewatch.rules.presets import Preset
from bluewatch.rules.text import approx_date, find_phrases, trunc, years_between

# Fields that describe what the company does (registry bookkeeping fields are left out).
DESCRIPTIVE_FIELDS = frozenset(
    {
        "product",
        "deployment",
        "pilot",
        "customers",
        "impact",
        "market",
        "certification",
        "programme",
        "grant",
        "award",
        "partners",
    }
)
PRE_LAUNCH = re.compile(r"\bwaitlist\b|\bcoming soon\b|\bpre-launch\b")
REGISTERS = {"FI": "PRH", "NO": "Brreg", "EE": "RIK"}
PUBLIC_FORMS = frozenset({"OYJ", "ASA", "AB (PUBL)", "PLC"})  # public limited companies: shares open to anyone
MAX_EMPLOYEES = 250  # the EU's upper bound for an SME
MAX_REVENUE_EUR = 10_000_000
ESTABLISHED = "An established company, outside a pre-seed to Series A window"
LATE_STAGE = "Series A or later, listed or acquired"


@dataclass(frozen=True)
class Part:
    value: float | None
    note: str


def company_text(company: Company, evidence: list[Evidence]) -> str:
    claims = [
        e.claim
        for e in evidence
        if e.state in ("fact", "assumption") and field_of(e) in DESCRIPTIVE_FIELDS and e.source_family != "crtsh"
    ]
    return " ".join([*company.names, company.one_liner or "", company.vertical_note or "", *claims])


def thesis_fit(company: Company, evidence: list[Evidence], preset: Preset) -> tuple[Part, str | None]:
    """Prior from the company's vertical, plus whole-word keyword hits; off-thesis words subtract.
    Returns the part and the preset vertical with most hits (None when nothing matched)."""
    text = company_text(company, evidence)
    prior = preset.vertical_prior.get(company.vertical or "none", preset.vertical_prior["none"])
    hits = {key: find_phrases(text, v.keywords) for key, v in preset.verticals.items()}
    best = max(hits, key=lambda k: (len(hits[k]), k == company.vertical)) if any(hits.values()) else None
    words = sorted({w for found in hits.values() for w in found})
    off = find_phrases(text, preset.off_thesis_keywords)
    value = prior + min(0.25, 0.08 * len(words)) - (0.3 if off else 0.0)
    value = round(min(1.0, max(0.0, value)), 2)
    label = preset.verticals[best].label if best else (company.vertical or "unclassified")
    note = label + (f" ({', '.join(words[:4])})" if words else "")
    if off:
        note += f"; off-thesis: {', '.join(off)}"
    return Part(value, note), best


def founding(company: Company, evidence: list[Evidence]) -> tuple[date, str] | None:
    """The founding date and how we know it: "registered 2019 (PRH)" or "founded 2012 (company site)"."""
    if company.registry.founded:
        return company.registry.founded, f"registered {company.registry.founded.year} ({_register(company)})"
    for e in facts(evidence):
        if field_of(e) == "founded" and (day := approx_date(e.value or e.claim)):
            source = "register" if e.tag == "registry" else "company site" if is_self_reported(e) else "research pack"
            return day, f"founded {day.year} ({source})"
    return None


def founded_on(company: Company, evidence: list[Evidence]) -> date | None:
    found = founding(company, evidence)
    return found[0] if found else None


def age_years(company: Company, evidence: list[Evidence], today: date) -> float | None:
    founded = founded_on(company, evidence)
    return years_between(founded, today) if founded else None


def too_late(company: Company, evidence: list[Evidence], preset: Preset, today: date) -> str | None:
    """The first too-late gate the company meets, as its rule and source; None when no gate applies."""
    reg = company.registry
    if (reg.form or "").upper() in PUBLIC_FORMS:
        return f"public limited company ({reg.form}, {_register(company)})"
    found = founding(company, evidence)
    limit = preset.stage_window.max_age_years
    if found and years_between(found[0], today) >= limit:
        return f"{found[1]}, over {trunc(limit, 0)} years ago"
    if reg.employees is not None and reg.employees > MAX_EMPLOYEES:
        return f"{reg.employees:,} employees ({_register(company)}), over {MAX_EMPLOYEES}"
    revenue = _filed_revenue_eur(evidence)
    if revenue is not None and revenue > MAX_REVENUE_EUR:
        return f"revenue EUR {revenue:,} ({_register(company)}), over EUR {MAX_REVENUE_EUR:,}"
    return None


def past_window(assessment: Assessment) -> str | None:
    """Why investors and funding do not apply to a too-late company, with the gate it met, read back from its
    investment readiness: "Past the stage window: registered 2012 (PRH), over 10 years ago". None while the
    window is open."""
    if "too_late" not in assessment.flags:
        return None
    irl = next(lv for lv in assessment.levels if lv.key == "irl")
    # On the scale, the level itself closed the window (see stage_fit); off it, the gate is in the reason.
    rule = LATE_STAGE if irl.applicable else (irl.unknown_reason or "").removeprefix(f"{ESTABLISHED}: ")
    return f"Past the stage window: {rule}"


def _filed_revenue_eur(evidence: list[Evidence]) -> int | None:
    """Revenue in euros from filed accounts, when a register fact states it. No source fills it yet: Brreg's
    accounts register (regnskapsregisteret) is the planned one."""
    filed = [e for e in facts(evidence) if e.field == "revenue" and e.tag == "registry" and (e.value or "").isdigit()]
    return int(filed[0].value) if filed else None


def _register(company: Company) -> str:
    return REGISTERS.get(company.registry.country, "register") if company.registry.id else "company name"


def stage_fit(irl: ReadinessLevel, age: float | None, late: str | None, preset: Preset) -> Part:
    """Stage credit only inside the window. A closed gate is a known negative; an unknown age earns nothing,
    since a listed group with mature products reads like a late-stage startup on readiness alone."""
    window = preset.stage_window
    if late:
        return Part(0.0, f"too late: {late}")
    if irl.level is not None and irl.level >= 9:
        return Part(0.0, f"too late: {LATE_STAGE}")
    if age is None:
        return Part(None, "stage unknown: founding date not found")
    if irl.level is None:
        return Part(None, "stage unknown")
    if irl.level < window.irl_min:
        return Part(0.6, f"early: IRL {irl.level}, before the window")
    if irl.level > window.irl_max:
        return Part(0.3, f"IRL {irl.level}, at the edge of the window")
    return Part(1.0, f"in the window (IRL {irl.level})")


def venture_type(levels: list[ReadinessLevel], evidence: list[Evidence]) -> Part:
    if not any(field_of(e) == "product" for e in facts(evidence)):
        return Part(None, "what the company sells is unknown")
    trl = next(lv for lv in levels if lv.key == "trl")
    if not trl.applicable:
        return Part(0.5, "service or consumer business: a partner, mentor or client rather than an investment case")
    return Part(1.0, "product or technology company")


def traction(levels: list[ReadinessLevel]) -> Part:
    """A bonus from proof that others pay or invest; absence adds nothing and removes nothing."""
    by_key = {lv.key: lv.level for lv in levels}
    brl, irl = by_key.get("brl") or 0, by_key.get("irl") or 0
    if brl >= 7:
        return Part(1.0, "named customers or repeat public contracts")
    if brl >= 6:
        return Part(0.8, "a paid contract or test sale")
    if brl >= 5:
        return Part(0.6, "a pilot or named partner")
    if irl >= 4:
        return Part(0.5, "grant, accelerator or equity backing")
    return Part(0.0, "no traction found yet")


def is_pre_launch(company: Company, evidence: list[Evidence]) -> bool:
    return "pre_launch" in company.tags or bool(PRE_LAUNCH.search(company_text(company, evidence).lower()))
