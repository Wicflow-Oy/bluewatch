"""How much each piece of evidence counts, and which field it speaks to.

Quality follows the tag: primary records (registers, TED, CORDIS, SEDIA, the company's own reply)
count fully; pages our researchers opened count almost fully; a site claim counts fully only with a
quote verified on the page; search summaries are assumptions, never facts.
"""

from __future__ import annotations

from bluewatch.models import Evidence

TAG_QUALITY = {
    "registry": 1.0,
    "ted": 1.0,
    "cordis": 1.0,
    "sedia": 1.0,
    "company_reply": 1.0,
    "read": 0.9,
    "dossier": 0.6,
    "snippet": 0.3,
}

# Reader and seed field names vary; the rules speak in these canonical fields.
FIELD_ALIASES = {
    "customers_or_sites": "customers",
    "customer": "customers",
    "clients": "customers",
    "funding_events": "funding",
    "round": "funding",
    "investment": "funding",
    "share_issue": "funding",
    "team_size": "team",
    "impact_thesis": "impact",
    "impact_kpi": "impact",
    "pricing": "business_model",
    "revenue": "financials",
    "awards": "award",
    "cohort": "programme",
    "accelerator": "programme",
}

# The five checks every card carries (the gap ledger's standard unknowns).
CORE_FIELDS = ("product", "customers", "team", "funding", "public_contracts")

FIELD_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "market": ("market",),
    "product": ("product", "tech"),
    "deployment": ("product", "tech"),
    "pilot": ("product", "tech", "business_model"),
    "certification": ("product", "tech"),
    "team": ("team",),
    "business_model": ("business_model",),
    "customers": ("business_model", "marketing_distribution"),
    "public_contracts": ("business_model", "financials"),
    "competition": ("competition",),
    "partners": ("marketing_distribution",),
    "award": ("marketing_distribution",),
    "programme": ("marketing_distribution",),
    "financials": ("financials",),
    "grant": ("financials",),
    "tech": ("tech",),
    "trl": ("tech",),
    "marketing_distribution": ("marketing_distribution",),
    "funding": ("deal_dynamics",),
    "impact": ("impact",),
}


def field_of(e: Evidence) -> str:
    return FIELD_ALIASES.get(e.field, e.field)


def quality(e: Evidence) -> float:
    """0..1; 0 means the item does not count as evidence at all."""
    if e.tag in ("site", "llm"):
        if e.verified_quote:
            return 0.8 if e.tag == "site" else 0.7
        # An unverified machine extraction never counts; a curated site read counts as a weak claim.
        return 0.0 if e.tag == "llm" else 0.4
    return TAG_QUALITY.get(e.tag, 0.0)


def facts(evidence: list[Evidence]) -> list[Evidence]:
    """Facts that count, in input order."""
    return [e for e in evidence if e.state == "fact" and quality(e) > 0]


def is_none_found(e: Evidence) -> bool:
    """A checked source that returned nothing: known, but never a clean bill."""
    return e.value == "none_found"


def is_self_reported(e: Evidence) -> bool:
    return e.source_family.startswith("site:") or "self-reported" in e.claim.lower()
