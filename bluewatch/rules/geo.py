"""Country codes and the region sets the eligibility and geography rules use."""

from __future__ import annotations

from bluewatch.rules.text import find_phrases

COUNTRY_CODES = {
    "finland": "FI",
    "norway": "NO",
    "sweden": "SE",
    "denmark": "DK",
    "iceland": "IS",
    "estonia": "EE",
    "latvia": "LV",
    "lithuania": "LT",
    "poland": "PL",
    "germany": "DE",
    "spain": "ES",
    "faroe islands": "FO",
    "bulgaria": "BG",
    "united states": "US",
    "usa": "US",
    "switzerland": "CH",
    "netherlands": "NL",
    "portugal": "PT",
    "ireland": "IE",
    "luxembourg": "LU",
    "austria": "AT",
    "singapore": "SG",
    "belgium": "BE",
    "france": "FR",
    "italy": "IT",
    "united kingdom": "GB",
    "slovenia": "SI",
}

NORDIC = frozenset({"FI", "SE", "NO", "DK", "IS", "FO", "GL", "AX"})
BALTIC = frozenset({"EE", "LV", "LT"})
EU = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
    }
)
# Horizon Europe associated countries: general knowledge, not read in this run. The rule texts that
# rely on it say "EU Member State or Horizon associated country".
HORIZON_ASSOCIATED = frozenset(
    {
        "NO",
        "IS",
        "LI",
        "FO",
        "AL",
        "BA",
        "GE",
        "IL",
        "XK",
        "MD",
        "ME",
        "MK",
        "RS",
        "TN",
        "TR",
        "UA",
        "GB",
        "CH",
        "NZ",
        "CA",
        "KR",
        "AM",
    }
)
EUROPE = EU | HORIZON_ASSOCIATED


def country_code(name: str | None) -> str | None:
    """ISO 3166-1 alpha-2 from a country name or code; None when the text names no known country."""
    if not name:
        return None
    text = name.strip()
    if len(text) == 2 and text.isalpha():
        return text.upper()
    lowered = text.lower()
    for country, code in COUNTRY_CODES.items():
        if lowered.startswith(country):
            return code
    return None


def countries_named(text: str) -> set[str]:
    return {COUNTRY_CODES[name] for name in find_phrases(text, list(COUNTRY_CODES))}
