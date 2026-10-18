"""The gap ledger: every claim is a fact, an assumption, an unknown or not applicable.

The five standard checks (product, customers, team, funding, public contracts) always appear: any
the evidence does not cover becomes an unknown with its cheapest next check, so a thin card shows
what to find out next instead of looking empty. So does every one of the ten dimensions no ledger item
speaks to, so each unknown dimension on the card has a ledger entry that says how it gets closed.
"""

from __future__ import annotations

from bluewatch.labels import DIMENSION_LABELS
from bluewatch.models import DIMENSIONS, Company, Evidence, GapLedger, NextCheck
from bluewatch.rules.evidence import CORE_FIELDS, FIELD_DIMENSIONS, field_of
from bluewatch.rules.readiness import trl_level

# Where to look when a dimension has no evidence yet.
NEXT_LOOK = {
    "market": "regulation-driven demand and public tenders in the segment (TED)",
    "product": "a live product, demo or pilot on the company's site",
    "team": "the team page on the company's site (roles only)",
    "business_model": "a pricing page and who pays",
    "competition": "named alternatives on the company's site",
    "marketing_distribution": "channel partners, events and press",
    "financials": "filed accounts and grants received",
    "tech": "patents, publications and readiness evidence",
    "deal_dynamics": "share-issue notices and announced rounds",
    "impact": "an impact claim mapped to an impact area, with a KPI",
}

FUNDING_CHECK = {
    "FI": "PRH trade-register notices by business ID, monthly",
    "NO": "Brreg announcements by organisation number, monthly",
    "EE": "RIK e-Business Register filings, monthly",
}


def ledger(company: Company, evidence: list[Evidence]) -> GapLedger:
    items = list(evidence)
    covered = {field_of(e) for e in items}
    items += [_standard_unknown(company, f) for f in CORE_FIELDS if f not in covered]
    trl = trl_level(evidence)
    if not trl.applicable and "trl" not in covered:
        items.append(
            Evidence(
                id=f"{company.id}#gap-trl",
                company_id=company.id,
                field="trl",
                claim="TRL: not applicable",
                source_family="gap_ledger",
                tag="dossier",
                state="not_applicable",
                why_unknown=trl.unknown_reason,
            )
        )
    spoken_to = {d for e in items for d in FIELD_DIMENSIONS.get(field_of(e), ())}
    items += [_dimension_unknown(company, d) for d in DIMENSIONS if d not in spoken_to]
    return GapLedger(
        company_id=company.id,
        facts=[e for e in items if e.state == "fact"],
        assumptions=[e for e in items if e.state == "assumption"],
        unknowns=[e for e in items if e.state == "unknown"],
        not_applicable=[e for e in items if e.state == "not_applicable"],
    )


def _standard_unknown(company: Company, field: str) -> Evidence:
    has_id = bool(company.registry.id)
    checks = {
        "product": NextCheck(
            kind="public_check",
            how="Re-read the company's site for a product or service page",
            question="What do you offer today, and is it live?",
        ),
        "customers": NextCheck(kind="ask_founder", question="Which customers, pilots or sites do you work with today?"),
        "team": NextCheck(
            kind="public_check",
            how="Re-read the site's team page in 4 weeks",
            question="Who is on the team (roles), and what is their background in this field?",
        ),
        "funding": NextCheck(
            kind="public_check",
            how=FUNDING_CHECK.get(company.registry.country, "The company's news page and press"),
            question="Have you raised equity or received grants so far?",
        ),
        "public_contracts": NextCheck(
            kind="public_check",
            how="TED winner-identifier query, weekly"
            if has_id
            else "Resolve the business ID first, then query TED by winner ID",
        ),
    }
    return Evidence(
        id=f"{company.id}#gap-{field}",
        company_id=company.id,
        field=field,
        claim=f"{field.replace('_', ' ').capitalize()}: unknown",
        source_family="gap_ledger",
        tag="dossier",
        state="unknown",
        why_unknown=f"No {field.replace('_', ' ')} evidence in the sources read",
        next_check=checks[field],
    )


def _dimension_unknown(company: Company, dimension: str) -> Evidence:
    label = DIMENSION_LABELS[dimension]
    return Evidence(
        id=f"{company.id}#gap-{dimension}",
        company_id=company.id,
        field=dimension,
        claim=f"{label}: unknown",
        source_family="gap_ledger",
        tag="dossier",
        state="unknown",
        why_unknown=f"No {label.lower()} evidence in the sources read",
        next_check=NextCheck(kind="public_check", how=f"Look for {NEXT_LOOK[dimension]}"),
    )
