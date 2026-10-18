"""The ten investment dimensions, each a fact, an assumption, unknown or not applicable, with the
evidence behind it. A dimension is a fact only when a sourced fact supports it; unknown is never zero."""

from __future__ import annotations

from bluewatch.models import DIMENSIONS, Company, DimensionState, Evidence
from bluewatch.rules.evidence import FIELD_DIMENSIONS, field_of, is_none_found, quality
from bluewatch.rules.gaps import NEXT_LOOK, ledger
from bluewatch.rules.readiness import trl_level


def assess_dimensions(company: Company, evidence: list[Evidence]) -> list[DimensionState]:
    """Read from the gap ledger, so an unknown dimension points at the ledger entry that closes it."""
    gl = ledger(company, evidence)
    items = gl.facts + gl.assumptions + gl.unknowns
    tech_applies = trl_level(evidence).applicable
    return [_dimension(key, items, tech_applies) for key in DIMENSIONS]


def _dimension(key: str, evidence: list[Evidence], tech_applies: bool) -> DimensionState:
    if key == "tech" and not tech_applies:
        return DimensionState(
            key=key, state="not_applicable", note="No technology to assess (service or consumer business)"
        )
    related = [e for e in evidence if key in FIELD_DIMENSIONS.get(field_of(e), ())]
    found = [e for e in related if e.state == "fact" and quality(e) > 0]
    if found:
        checked_empty = all(is_none_found(e) for e in found)
        note = "checked; none found in this source" if checked_empty else f"{len(found)} sourced fact(s)"
        return DimensionState(key=key, state="fact", evidence_ids=[e.id for e in found], note=note)
    assumed = [e for e in related if e.state == "assumption"]
    if assumed:
        return DimensionState(
            key=key,
            state="assumption",
            evidence_ids=[e.id for e in assumed],
            note=assumed[0].basis or "unconfirmed claim",
        )
    unknown = [e for e in related if e.state == "unknown"]
    why = unknown[0].why_unknown if unknown and unknown[0].why_unknown else "no evidence read yet"
    return DimensionState(
        key=key, state="unknown", evidence_ids=[e.id for e in unknown], note=f"{why}; look for {NEXT_LOOK[key]}"
    )
