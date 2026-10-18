"""TRL, BRL (KTH), ocean impact and investment readiness from public evidence.

Each level is the highest one a fact supports (cues in scales.py), with the supporting evidence ids,
a confidence and what would raise it. No supporting fact means level=None with a reason: unknown is
never 0. A service company has no TRL (applicable=False).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bluewatch.config import settings
from bluewatch.models import Company, Evidence, ReadinessLevel
from bluewatch.rules import scales
from bluewatch.rules.evidence import facts, field_of, is_none_found, is_self_reported
from bluewatch.rules.fit import ESTABLISHED, too_late
from bluewatch.rules.presets import Preset, load_preset

PRIMARY_TAGS = frozenset({"registry", "ted", "cordis", "sedia", "company_reply"})
PRODUCT_FIELDS = frozenset({"product", "deployment", "pilot", "certification", "customers"})
IMPACT_FIELDS = PRODUCT_FIELDS | {"impact", "grant", "award", "programme"}
IMPACT_WORDS = {1: "intent", 2: "defined", 3: "piloted", 4: "validated", 5: "embedded"}


@dataclass
class Hit:
    level: int
    label: str
    evidence: list[Evidence]


def assess_levels(
    company: Company, evidence: list[Evidence], *, preset: str | Preset = "blue", today: date | None = None
) -> list[ReadinessLevel]:
    p = load_preset(preset) if isinstance(preset, str) else preset
    usable = facts(evidence)
    brl = _brl(usable)
    late = too_late(company, evidence, p, today or settings().today)
    irl = _established(late) if late else _level("irl", _irl(usable, brl))
    return [trl_level(evidence), _level("brl", brl), _impact(usable, p), irl]


# --------------------------------------------------------------------------- TRL
def trl_level(evidence: list[Evidence]) -> ReadinessLevel:
    usable = facts(evidence)
    stated = next((e for e in evidence if e.state == "not_applicable" and field_of(e) == "trl"), None)
    if stated:
        return ReadinessLevel(
            key="trl",
            applicable=False,
            evidence_ids=[stated.id],
            confidence="medium",
            unknown_reason=stated.why_unknown or "Technology readiness does not apply",
        )
    not_tech = _not_a_technology(usable)
    if not_tech:
        reason, ids = not_tech
        return ReadinessLevel(key="trl", applicable=False, evidence_ids=ids, confidence="low", unknown_reason=reason)
    hits = _cue_hits(scales.TRL_CUES, usable)
    named = [e for e in usable if re.search(scales.TRL_NAMED_PILOT, e.claim)]
    if named:
        hits.append(Hit(7, "field pilot with a named partner", named))
    awards = _awards(usable)
    if awards:
        hits.append(Hit(8, "first commercial deliveries (public contract award)", awards))
    return _level("trl", _best(hits))


def _not_a_technology(usable: list[Evidence]) -> tuple[str, list[str]] | None:
    product = [e for e in usable if field_of(e) in PRODUCT_FIELDS and e.source_family != "crtsh"]
    if not product:
        return None
    text = " ".join(e.claim.lower() for e in product)
    if re.search(scales.TECH_CUES, text):
        return None
    ids = [e.id for e in product]
    if re.search(scales.CONSUMER_CUES, text):
        return "Consumer product, not a technology: technology readiness does not apply", ids
    if re.search(scales.SERVICE_CUES, text):
        return "Service company: technology readiness does not apply", ids
    return None


# --------------------------------------------------------------------------- BRL
def _brl(usable: list[Evidence]) -> Hit | None:
    hits = _cue_hits(scales.BRL_CUES, usable)
    awards = _awards(usable)
    buyers = {_buyer(e) for e in awards}
    if len(buyers) >= 2:
        hits.append(Hit(7, f"public contracts from {len(buyers)} buyers", awards))
    elif awards:
        hits.append(Hit(6, "a public contract award (test sale)", awards))
    described = [e for e in usable if field_of(e) == "product" and e.source_family != "crtsh"]
    if described:
        hits.append(Hit(2, "the offer is described on a public page", described[:1]))
    return _best(hits)


def _awards(usable: list[Evidence]) -> list[Evidence]:
    return [e for e in usable if field_of(e) == "public_contracts" and e.tag == "ted" and not is_none_found(e)]


def _buyer(e: Evidence) -> str:
    m = re.search(r"\(buyer: ([^)]+)\)", e.claim)
    return m.group(1) if m else e.id


# --------------------------------------------------------------------------- IRL
def _irl(usable: list[Evidence], brl: Hit | None) -> Hit | None:
    hits = _cue_hits(scales.IRL_CUES, usable)
    registered = [e for e in usable if field_of(e) == "founded" and e.tag == "registry"]
    if registered:
        hits.append(Hit(3, "company registered", registered[:1]))
    if brl and brl.level >= 7:
        hits.append(Hit(7, "repeatable traction (team completeness not known)", brl.evidence))
    elif brl and brl.level >= 5:
        hits.append(Hit(brl.level, "first revenue" if brl.level == 6 else "a pilot or partner", brl.evidence))
    return _best(hits)


def _established(late: str) -> ReadinessLevel:
    """Investment readiness is a startup scale: an established company is not on it, so a register date
    or a company form never becomes a level."""
    return ReadinessLevel(
        key="irl",
        applicable=False,
        confidence="medium",
        unknown_reason=f"{ESTABLISHED}: {late}",
    )


# --------------------------------------------------------------------------- ocean impact
def _impact(usable: list[Evidence], preset: Preset) -> ReadinessLevel:
    candidates = [e for e in usable if field_of(e) in IMPACT_FIELDS and e.source_family != "crtsh"]
    area_levels: dict[str, tuple[int | None, list[Evidence]]] = {}
    for area, words in preset.impact.areas.items():
        mentions = [e for e in candidates if _mentions(e.claim, words)]
        if not mentions:
            continue
        scored = [(_impact_level(e), e) for e in mentions]
        best = max((lvl for lvl, _ in scored if lvl is not None), default=None)
        support = [e for lvl, e in scored if lvl == best] if best else mentions
        area_levels[area] = (best, support)
    if not area_levels:
        return ReadinessLevel(
            key="oirl",
            unknown_reason="No impact claim or impact area found in the evidence",
            raise_by=scales.raise_by("oirl", None),
        )
    ordered = sorted(area_levels, key=lambda a: (-(area_levels[a][0] or 0), a))
    level, support = area_levels[ordered[0]]
    common = dict(
        key="oirl",
        areas=ordered,
        evidence_ids=[e.id for e in support],
        thesis_quote=support[0].quote or support[0].claim,
        raise_by=scales.raise_by("oirl", level),
    )
    if level is None:
        return ReadinessLevel(
            **common,
            unknown_reason=(
                f"Area inferred from what the company does ({preset.impact.name}); no impact claim or mechanism read"
            ),
        )
    return ReadinessLevel(**common, level=level, band=IMPACT_WORDS[level], confidence=_confidence(support))


def _mentions(claim: str, words: list[str]) -> bool:
    text = claim.lower()
    return any(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text) for w in words)


def _impact_level(e: Evidence) -> int | None:
    text = e.claim.lower()
    if not (field_of(e) == "impact" or re.search(scales.IMPACT_MECHANISM, text)):
        return None
    level = 1
    if re.search(scales.IMPACT_KPI, text):
        level = 2
        if "pilot" in text:
            level = 3
        if re.search(scales.IMPACT_VALIDATED, text) and "not verified" not in text:
            level = 4
    if re.search(scales.IMPACT_EMBEDDED, text):
        level = 5
    # Self-reported figures cap at 3: a company's own number is a claim, not a validated result.
    return min(level, 3) if is_self_reported(e) else level


# --------------------------------------------------------------------------- shared
def _cue_hits(cues: tuple[scales.Cue, ...], usable: list[Evidence]) -> list[Hit]:
    hits = []
    for level, pattern, label in cues:
        matched = [e for e in usable if re.search(pattern, e.claim.lower())]
        if matched:
            hits.append(Hit(level, label, matched))
    return hits


def _best(hits: list[Hit]) -> Hit | None:
    return max(hits, key=lambda h: h.level) if hits else None


def _level(key: str, hit: Hit | None) -> ReadinessLevel:
    if hit is None:
        reason = {
            "trl": "No public evidence of a prototype, pilot or deployment",
            "brl": "No public description of the offer",
            "irl": "No register record or funding milestone found",
        }[key]
        return ReadinessLevel(key=key, unknown_reason=reason, raise_by=scales.raise_by(key, None))
    return ReadinessLevel(
        key=key,
        level=hit.level,
        band=_band(hit.level),
        confidence=_confidence(hit.evidence),
        evidence_ids=[e.id for e in hit.evidence],
        raise_by=scales.raise_by(key, hit.level),
    )


def _band(level: int) -> str:
    return "1-3" if level <= 3 else "4-6" if level <= 6 else "7-9"


def _confidence(support: list[Evidence]) -> str:
    """High: two or more independent sources. Medium: one primary or researcher-read source.
    Low: the company's own claims only."""
    independent = {e.source_family for e in support if not is_self_reported(e)}
    if len(independent) >= 2:
        return "high"
    if any(e.tag in PRIMARY_TAGS or (e.tag == "read" and not is_self_reported(e)) for e in support):
        return "medium"
    return "low"
