"""The demo companies the generators link: startups.json plus the curated weekly-list rows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from bluewatch import seed
from bluewatch.bridges.common import first_iso_date, fmt_day, norm_name
from bluewatch.models import BridgeEvidence, BridgeParty

COUNTRY_CODES = {
    "Finland": "FI",
    "Norway": "NO",
    "Sweden": "SE",
    "Denmark": "DK",
    "Iceland": "IS",
    "Estonia": "EE",
    "Latvia": "LV",
    "Lithuania": "LT",
    "Poland": "PL",
    "Germany": "DE",
    "Spain": "ES",
    "Faroe Islands": "FO",
    "Bulgaria": "BG",
    "Switzerland": "CH",
    "United States": "US",
}
COUNTRY_NAMES = {code: name for name, code in COUNTRY_CODES.items()}
REGISTERS = {"FI", "NO", "EE"}
# Research notes inside startups.json descriptions: where a line came from or how well it fits, never what
# the company does. A line only seen in search results is shown as a snippet instead of the company's site.
SEARCH_ONLY_NOTE = re.compile(r"\s*\((?:search-result summary only|search snippet)[^)]*\)")
FIT_NOTE = re.compile(r"\s*\(weak blue fit\)")
VERTICAL_NOUNS = {
    "maritime_ports": "maritime company",
    "ocean_infra_clean_energy": "ocean-energy company",
    "marine_intelligence": "ocean-data company",
    "blue_biotech_water": "blue-bio company",
}


def registry_url(country: str | None, registry_id: str | None) -> str | None:
    if country == "FI" and registry_id:
        return f"https://avoindata.prh.fi/opendata-ytj-api/v3/companies?businessId={registry_id}"
    if country == "NO" and registry_id:
        return f"https://virksomhet.brreg.no/nb/oppslag/enheter/{registry_id}"
    return None


@dataclass(frozen=True)
class DemoCompany:
    name: str
    country: str | None
    registry_id: str | None
    registry_checked: bool  # the ID and founding date were read from PRH or Brreg
    city: str | None
    founded: date | None
    vertical: str | None
    vertical_note: str | None
    about: str  # what the company says it does
    about_read_on_site: bool  # False: the description was only seen in search results
    website: str | None
    older_scaleup: bool

    @property
    def company_id(self) -> str | None:
        return f"{self.country}:{self.registry_id}" if self.country and self.registry_id else None

    def party(self) -> BridgeParty:
        return BridgeParty(
            name=self.name,
            kind="company",
            country=self.country,
            registry_id=self.registry_id,
            company_id=self.company_id,
        )

    def anonymised_name(self) -> str:
        """Stands in for the name while a viewer hides names: 'A Rauma boat builder'."""
        noun = (
            "boat builder"
            if re.search(r"\bboats?\b", self.about, re.I)
            else VERTICAL_NOUNS.get(self.vertical or "", "company")
        )
        return f"A {self.city} {noun}" if self.city else f"A {noun}"

    def site_evidence(self) -> BridgeEvidence:
        return BridgeEvidence(claim=self.about, url=self.website, tag="site" if self.about_read_on_site else "snippet")

    def registry_evidence(self) -> BridgeEvidence | None:
        # The claim leaves the register ID to the source chip, so hiding names hides the ID too.
        if not (self.registry_checked and self.country in REGISTERS):
            return None
        where = f" in {self.city}" if self.city else ""
        return BridgeEvidence(
            claim=f"Founded {fmt_day(self.founded)}{where}" if self.founded else "Registered",
            url=registry_url(self.country, self.registry_id),
            date=self.founded.isoformat() if self.founded else None,
            tag="registry",
        )

    def age_years(self, today: date) -> float | None:
        return (today - self.founded).days / 365.25 if self.founded else None


def _registry_id(row: dict, country: str | None) -> str | None:
    ids = row.get("registry_ids") or {}
    values = ids.get(country) if country else None
    return values[0] if isinstance(values, list) and values else None


def _from_startup(row: dict) -> DemoCompany:
    country = COUNTRY_CODES.get(row["country"])
    check = row.get("registry_check") or {}
    founded = row.get("founded")
    founded_text = founded.get("value") if isinstance(founded, dict) else founded
    described = FIT_NOTE.sub("", "; ".join(x for x in (row.get("subsector"), row.get("one_liner")) if x))
    about = SEARCH_ONLY_NOTE.sub("", described)
    return DemoCompany(
        name=row["name"],
        country=country,
        registry_id=_registry_id(row, country),
        registry_checked=check.get("source") in ("PRH YTJ", "Brreg"),
        city=(check.get("municipality") or "").title() or None,
        founded=first_iso_date(str(founded_text)) or first_iso_date(check.get("founded") or check.get("registered")),
        vertical=row.get("vertical"),
        vertical_note=row.get("subsector"),
        about=about,
        about_read_on_site=about == described,
        website=row.get("website"),
        older_scaleup=bool(row.get("older_scaleup")),
    )


def _from_list_row(row: dict) -> DemoCompany:
    register, _, registry_id = row["registry"].partition(" ")
    country = {"PRH": "FI", "Brreg": "NO"}[register]
    vertical, _, note = row["vertical"].partition(" (")
    city = row["municipality"].split(" (")[0]
    site = next((u for u in row["sources"] if "prh.fi" not in u and "brreg.no" not in u), None)
    # The first reason is the founding date when the row is a new company; the site claim follows.
    description = row["why"][1] if row["why"][0].startswith("Founded") else row["why"][0]
    return DemoCompany(
        name=row["name"],
        country=country,
        registry_id=registry_id,
        registry_checked=True,
        city=None if city.startswith("see ") else city,
        founded=first_iso_date(row["founded"]),
        vertical=vertical if " " not in vertical else None,
        vertical_note=note.rstrip(")") or None,
        about=re.sub(r"\s*\(site[^)]*\)$", "", description),
        about_read_on_site=True,
        website=site,
        older_scaleup=False,
    )


@lru_cache(maxsize=1)
def demo_companies() -> tuple[DemoCompany, ...]:
    """Every demo company once, keyed by registry ID where there is one."""
    companies = [_from_startup(r) for r in seed.load("startups")["startups"]]
    known = {c.company_id for c in companies if c.company_id}
    for row in seed.load("demo_list_2026_10_12")["rows"]:
        company = _from_list_row(row)
        if company.company_id not in known:
            companies.append(company)
    return tuple(companies)


def by_registry_id(registry_id: str | None) -> DemoCompany | None:
    if not registry_id:
        return None
    return next((c for c in demo_companies() if c.registry_id == registry_id), None)


def by_exact_name(name: str) -> DemoCompany | None:
    """A unique exact (normalised) name match among the demo companies, else None."""
    matches = [c for c in demo_companies() if norm_name(c.name) == norm_name(name)]
    return matches[0] if len(matches) == 1 else None
