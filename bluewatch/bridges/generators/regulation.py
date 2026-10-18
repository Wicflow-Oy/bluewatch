"""The law creates a buyer: a dated regulation x a capability x a named buyer that must comply."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bluewatch import seed
from bluewatch.bridges.common import fmt_day, make_bridge, today_or_default
from bluewatch.bridges.companies import demo_companies
from bluewatch.models import Bridge, BridgeEvidence, BridgeParty


@dataclass(frozen=True)
class Regulation:
    """A regulation clock entry. Its text, date and URL come from evidence read into the seeds."""

    source_url: str
    need: str  # what the regulation makes buyers acquire
    capability: re.Pattern  # what a company must sell to serve the new buyers
    buyer_type: str  # partners.json entity type of the buyers who must comply
    buyer_evidence: re.Pattern  # what a buyer's record must show to be named


REGULATIONS = (
    Regulation(
        source_url="https://eur-lex.europa.eu/eli/reg/2023/1805/oj",  # FuelEU Maritime, read for seed B8
        need="shore power for ships at berth",
        capability=re.compile(r"\b(?:on)?shore (?:power|charging)\b", re.I),
        buyer_type="port",
        buyer_evidence=re.compile(r"\bonshore power\b", re.I),
    ),
)


def _seed_evidence(url: str) -> BridgeEvidence | None:
    """The regulation as read for the seed pack; without it the regulation is not used."""
    for bridge in seed.load("bridges")["bridges"]:
        for item in bridge["evidence_counterparty"]:
            if item.get("url") == url and item.get("tag") == "read" and item.get("date"):
                return BridgeEvidence(**item)
    return None


def _buyers(regulation: Regulation) -> list[tuple[dict, str]]:
    found = []
    for entity in seed.load("partners")["entities"]:
        if entity["type"] != regulation.buyer_type:
            continue
        for text in entity["eu_projects"]:
            if regulation.buyer_evidence.search(text):
                found.append((entity, text))
                break
    return found


def law_creates_buyer(*, today: date | None = None) -> list[Bridge]:
    today = today_or_default(today)
    bridges = []
    for regulation in REGULATIONS:
        law = _seed_evidence(regulation.source_url)
        if law is None:
            continue
        applies_from = date.fromisoformat(law.date)
        if applies_from < today:
            continue
        for company in demo_companies():
            capability = regulation.capability.search(company.about)
            if not capability:
                continue
            for buyer, text in _buyers(regulation):
                short = buyer["name"].split(" (")[0]
                weak = "search_snippet" in buyer["verification"]
                bridges.append(
                    make_bridge(
                        type="law_creates_buyer",
                        company=company.party(),
                        counterparty=BridgeParty(name=buyer["name"], kind=buyer["type"], country=buyer["country"]),
                        reason=(
                            f"{law.claim.split(',')[0]} requires {regulation.need} from {fmt_day(applies_from)}; "
                            f"{short} already has a project on it; the company sells "
                            f"{capability.group(0).lower()}"
                        ),
                        evidence_company=[company.site_evidence()],
                        evidence_counterparty=[
                            law,
                            BridgeEvidence(
                                claim=f"{buyer['name']}: {text}",
                                url=(buyer["source_urls"] or [None])[0],
                                tag="snippet" if weak else "read",
                            ),
                        ],
                        join="partial",  # the buyer's purchase plans are not read, only its project
                        deadline=applies_from,
                        action=f"Track {short}'s tenders for {regulation.need} on TED ahead of {applies_from.year}",
                        caveat="The buyer side is a project record, not a tender"
                        + ("; its text is a search summary" if weak else ""),
                        mode="redstone",
                    )
                )
    return bridges
