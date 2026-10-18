"""The two-axis score. Potential comes from fit and signals; evidence is how much of it is sourced.

Unknowns lower only the evidence axis: an unknown potential part is left out of the average (never
counted as zero), and traction only ever adds. Known negatives (off-thesis, too late) do lower
potential, because they are facts, not gaps; too late closes it to 0, since no fit makes an established
company a pre-seed to Series A case, and so does a register that lists the company as closed.
"""

from __future__ import annotations

from datetime import date, timedelta

from bluewatch.config import settings
from bluewatch.models import Company, Evidence, ReadinessLevel, Score
from bluewatch.rules import gaps
from bluewatch.rules.evidence import CORE_FIELDS, field_of, is_none_found, quality
from bluewatch.rules.fit import (
    Part,
    age_years,
    is_pre_launch,
    stage_fit,
    thesis_fit,
    too_late,
    traction,
    venture_type,
)
from bluewatch.rules.presets import Preset, load_preset
from bluewatch.rules.text import humanise_keys, trunc
from bluewatch.sources.common import is_closed, not_trading

ASSUMPTION_CREDIT = 0.3  # an assumption with a stated basis is worth something, far less than a fact
NONE_FOUND_CREDIT = 0.5  # "checked, nothing found" is known, but never a clean bill


def score(
    company: Company,
    evidence: list[Evidence],
    levels: list[ReadinessLevel],
    *,
    preset: str | Preset = "blue",
    today: date | None = None,
) -> Score:
    p = load_preset(preset) if isinstance(preset, str) else preset
    today = today or settings().today
    fit, _ = thesis_fit(company, evidence, p)
    irl = next(lv for lv in levels if lv.key == "irl")
    stage = stage_fit(irl, age_years(company, evidence, today), too_late(company, evidence, p, today), p)
    venture = venture_type(levels, evidence)
    bonus = traction(levels)

    parts = {"thesis_fit": fit, "stage_fit": stage, "venture_type": venture}
    known = {k: part for k, part in parts.items() if part.value is not None}
    weights = p.weights.potential
    base = sum(weights[k] * part.value for k, part in known.items()) / sum(weights[k] for k in known)
    late = stage.value == 0.0
    closed = is_closed(company.registry.status)
    potential = 0.0 if late or closed else round(min(1.0, base + p.traction_bonus * bonus.value), 3)
    potential_parts = {k: part.value for k, part in known.items()} | {
        "traction_bonus": round(p.traction_bonus * bonus.value, 3)
    }

    evidence_parts, counts = _evidence_parts(company, evidence, today)
    ew = p.weights.evidence
    evidence_score = round(sum(ew[k] * v for k, v in evidence_parts.items()), 3)

    group, why_group = _group(potential, evidence_score, fit, stage, company, evidence, p)
    explanation = [
        f"Potential {trunc(potential)}: "
        + "; ".join(f"{humanise_keys(k)} {trunc(part.value)} ({humanise_keys(part.note)})" for k, part in known.items())
        + (f"; traction +{trunc(potential_parts['traction_bonus'])} ({bonus.note})" if bonus.value else ""),
        "Too late closes potential to 0, whatever the other parts" if late else "",
        _unknown_parts_line(parts),
        f"Evidence {trunc(evidence_score)}: {_n(counts['facts'], 'fact')}, {_n(counts['assumptions'], 'assumption')}, "
        f"{_n(counts['unknowns'], 'unknown')} across the five standard checks; unknowns lower this axis only",
        why_group,
    ]
    return Score(
        potential=potential,
        evidence=evidence_score,
        group=group,
        potential_parts=potential_parts,
        evidence_parts=evidence_parts,
        explanation=[line for line in explanation if line],
    )


def _n(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _evidence_parts(company: Company, evidence: list[Evidence], today: date) -> tuple[dict[str, float], dict]:
    ledger = gaps.ledger(company, evidence)
    items = ledger.facts + ledger.assumptions + ledger.unknowns + ledger.not_applicable
    coverage = []
    for core in CORE_FIELDS:
        related = [e for e in items if field_of(e) == core]
        if any(e.state == "not_applicable" for e in related):
            continue
        credits = [quality(e) * (NONE_FOUND_CREDIT if is_none_found(e) else 1.0) for e in related if e.state == "fact"]
        credits += [ASSUMPTION_CREDIT for e in related if e.state == "assumption"]
        coverage.append(max(credits, default=0.0))
    counted = [e for e in ledger.facts if quality(e) > 0]
    fresh_after = today - timedelta(days=180)
    recent = [e for e in counted if e.retrieved_at and e.retrieved_at.date() >= fresh_after]
    parts = {
        "coverage": round(sum(coverage) / len(coverage), 3) if coverage else 0.0,
        "independence": round(min(1.0, len({e.source_family for e in counted}) / 3), 3),
        "recency": round(len(recent) / len(counted), 3) if counted else 0.0,
    }
    core_unknowns = [e for e in ledger.unknowns if field_of(e) in CORE_FIELDS]
    counts = {"facts": len(counted), "assumptions": len(ledger.assumptions), "unknowns": len(core_unknowns)}
    return parts, counts


def _group(
    potential: float,
    evidence: float,
    fit: Part,
    stage: Part,
    company: Company,
    evidence_items: list[Evidence],
    p: Preset,
) -> tuple[str, str]:
    t = p.thresholds
    if company.registry.natural_person:
        return "not_for_us", "Not for us: a sole trader is a private person and is never ranked"
    if is_closed(company.registry.status):  # a company that no longer trades is no case at any fit
        return "not_for_us", closed_rule(company.registry.status)
    if stage.value == 0.0:  # too late comes first: for an established company it is the deciding fact
        return "not_for_us", f"Not for us: {stage.note}"
    if fit.value is not None and fit.value < t.off_thesis:
        return "not_for_us", f"Not for us: off-thesis for the {p.label} preset ({fit.note})"
    if is_pre_launch(company, evidence_items):
        return "not_yet", "Not yet: pre-launch page only; stays in the watch window"
    if potential < t.promising:
        return "not_yet", f"Not yet: potential {trunc(potential)} is below {trunc(t.promising)}"
    if evidence >= t.solid_evidence:
        return "act_now", "Act now: promising, and the evidence is solid"
    return "dive_deeper", "Dive deeper: promising, but the evidence is thin; missing information is the next step"


def closed_rule(status: str) -> str:
    return f"Not for us: {not_trading(status)}"


def _unknown_parts_line(parts: dict[str, Part]) -> str:
    unknown = [k.replace("_", " ") for k, part in parts.items() if part.value is None]
    return f"Unknown, so left out of potential: {', '.join(unknown)}" if unknown else ""
