"""The 10 hand-verified seed bridges from data/seed/bridges_seed.json, as C7 Bridge objects."""

from __future__ import annotations

from bluewatch import seed
from bluewatch.bridges.common import identifying_terms_for
from bluewatch.bridges.companies import by_exact_name, by_registry_id
from bluewatch.models import Bridge, BridgeEvidence, BridgeParty


def _company(raw: dict) -> BridgeParty:
    registry = raw.get("registry") or {}
    country, registry_id = registry.get("country"), registry.get("id")
    # Where the seed leaves the ID empty, link the demo company only on a unique exact name match.
    match = by_registry_id(registry_id) if registry_id else by_exact_name(raw["name"])
    company_id = f"{country}:{registry_id}" if registry_id else (match.company_id if match else None)
    return BridgeParty(
        name=raw["name"],
        kind=raw.get("kind", "company"),
        country=country,
        registry_id=registry_id,
        company_id=company_id,
    )


def _evidence(items: list[dict]) -> list[BridgeEvidence]:
    return [BridgeEvidence(**item) for item in items]


def _bridge(raw: dict) -> Bridge:
    company = _company(raw["company"])
    match = by_registry_id(company.registry_id) if company.registry_id else None
    return Bridge(
        id=raw["id"],
        type=raw["type"],
        company=company,
        counterparty=BridgeParty(**raw["counterparty"]),
        reason=raw["reason"],
        evidence_company=_evidence(raw["evidence_company"]),
        evidence_counterparty=_evidence(raw["evidence_counterparty"]),
        deadline=raw["deadline"],
        action=raw["action"],
        confidence=raw["confidence"],
        caveat=raw.get("caveat"),
        mode=raw["mode"],
        anonymised_name=match.anonymised_name() if match else None,
        identifying_terms=identifying_terms_for(company, raw.get("identifying_terms", [])),
    )


def seed_bridges() -> list[Bridge]:
    return [_bridge(raw) for raw in seed.load("bridges")["bridges"]]
