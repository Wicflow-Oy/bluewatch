"""Display names and labels in one place, so a rename is one edit (or one env var)."""

from __future__ import annotations

import os

from bluewatch.models import Group, LevelKey, Mode, Tier

PRODUCT_NAME = os.environ.get("BLUEWATCH_PRODUCT_NAME") or "BlueWatch"
LIST_NAME = os.environ.get("BLUEWATCH_LIST_NAME") or "Now Surfacing"

GROUP_LABELS: dict[Group, str] = {
    "act_now": "Act now",
    "dive_deeper": "Dive deeper",
    "not_yet": "Not yet",
    "not_for_us": "Not for us",
}

GROUP_RULE = (
    "Act now = high potential and solid evidence. Dive deeper = promising but thin evidence "
    "(unknowns lower evidence, never potential). Not yet = too early or weak fit."
)

TIER_LABELS: dict[Mode, dict[Tier, str]] = {
    "apelago": {
        "certain": "Likely",
        "likely": "Likely",
        "possible": "Possible",
        "excluded": "Unlikely",
        "unknown": "Unknown",
    },
    "redstone": {
        "certain": "Certain*",
        "likely": "Probable",
        "possible": "Possible",
        "excluded": "Excluded",
        "unknown": "Unknown",
    },
}

LEVEL_LABELS: dict[Mode, dict[LevelKey, str]] = {
    "apelago": {
        "trl": "Tech readiness",
        "brl": "Business readiness",
        "oirl": "Ocean impact",
        "irl": "Investment readiness",
    },
    "redstone": {
        "trl": "TRL",
        "brl": "BRL (KTH)",
        "oirl": "Ocean impact (our 1-5 scale)",
        "irl": "Investment readiness (1-9)",
    },
}

DIMENSION_LABELS = {
    "market": "Market",
    "product": "Product",
    "team": "Team",
    "business_model": "Business model",
    "competition": "Competition",
    "marketing_distribution": "Marketing and distribution",
    "financials": "Financials",
    "tech": "Tech",
    "deal_dynamics": "Deal dynamics",
    "impact": "Impact",
}

SOURCE_LABELS = {
    "prh": "Finland company register (PRH)",
    "brreg": "Norway company register (Brreg)",
    "rik": "Estonia company register (RIK)",
    "scb": "Sweden business register (SCB)",
    "ted": "EU public tenders (TED)",
    "cordis": "EU research projects (CORDIS)",
    "interreg": "Interreg Central Baltic",
    "vies": "EU VAT check (VIES)",
}

ATTRIBUTION = (
    "Sources: Finnish Patent and Registration Office (PRH, CC BY 4.0); Brønnøysund Register Centre "
    "(NLOD); Estonian e-Business Register (RIK, CC BY 4.0); TED and CORDIS (European Union, CC BY 4.0)."
)
