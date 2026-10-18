"""One call from a company and its evidence to a full, versioned Assessment."""

from __future__ import annotations

from datetime import datetime, time, timezone

from bluewatch.config import settings
from bluewatch.models import Assessment, Company, Evidence, ReadinessLevel, Score
from bluewatch.rules.dimensions import assess_dimensions
from bluewatch.rules.evidence import facts, is_self_reported
from bluewatch.rules.fit import is_pre_launch
from bluewatch.rules.presets import load_preset
from bluewatch.rules.readiness import assess_levels
from bluewatch.rules.score import score
from bluewatch.rules.version import rules_version
from bluewatch.sources.common import is_closed


def assess(
    company: Company, evidence: list[Evidence], *, preset: str = "blue", now: datetime | None = None
) -> Assessment:
    # Noon on the configured "today", so the same input gives the same assessment all day.
    now = now or datetime.combine(settings().today, time(12), tzinfo=timezone.utc)
    p = load_preset(preset)
    levels = assess_levels(company, evidence, preset=p, today=now.date())
    s = score(company, evidence, levels, preset=p, today=now.date())
    return Assessment(
        company_id=company.id,
        levels=levels,
        dimensions=assess_dimensions(company, evidence),
        flags=_flags(company, evidence, levels, s),
        score=s,
        rules_version=rules_version(),
        preset=p.name,
        assessed_at=now,
    )


def _flags(company: Company, evidence: list[Evidence], levels: list[ReadinessLevel], s: Score) -> list[str]:
    by_key = {lv.key: lv for lv in levels}
    flags = []
    if company.registry.natural_person:
        flags.append("natural_person")
    if is_closed(company.registry.status):
        flags.append("closed")
    if company.resolution.state not in ("resolved", "probable"):
        flags.append("identity_not_confirmed")
    if not by_key["trl"].applicable:
        flags.append("no_technology_readiness")
    if is_pre_launch(company, evidence):
        flags.append("pre_launch")
    if by_key["oirl"].level == 1:
        flags.append("impact_claim_without_kpi")  # the greenwashing check: a claim with no measure
    counted = [e for e in facts(evidence) if e.tag != "registry"]
    if counted and all(is_self_reported(e) for e in counted):
        flags.append("self_reported_only")
    if s.potential_parts.get("stage_fit") == 0.0:
        flags.append("too_late")
    return flags
