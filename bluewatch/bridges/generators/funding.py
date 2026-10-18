"""Bridges from grants.json: the rule decides, proof steps and programme fit."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bluewatch import seed
from bluewatch.bridges.common import fmt_day, make_bridge, today_or_default
from bluewatch.bridges.companies import COUNTRY_NAMES, DemoCompany, demo_companies
from bluewatch.models import Bridge, BridgeEvidence, BridgeParty

BLUE_VERTICALS = {"maritime_ports", "ocean_infra_clean_energy", "marine_intelligence", "blue_biotech_water"}
NORDIC_BALTIC = frozenset({"FI", "SE", "NO", "DK", "IS", "FO", "EE", "LV", "LT", "PL", "DE"})

# Technology classes for proof-step instruments, keyed by the instrument's themes in grants.json.
TECH_TERMS = {
    "ocean_observation": r"observ\w*|buoys?|hydrograph\w*|oceanograph\w*|water[- ]quality",
    "marine_sensors": r"sensors?|sensing|sonar|multibeam|echo ?sound\w*|underwater (?:imaging|robots?|drones?)",
}
EXPERT_TERMS = re.compile(r"\b(consult\w*|advis\w*|training)\b", re.I)


@dataclass(frozen=True)
class ProgrammeRule:
    """Stage and place for a programme; `unchecked` names the criteria we cannot see."""

    instrument_id: str
    max_age_years: int
    countries: frozenset[str] | None  # None: open worldwide
    unchecked: str


PROGRAMMES = (
    ProgrammeRule("apelago-northern-blue-2027", 10, NORDIC_BALTIC, "Eligibility criteria are not published"),
    ProgrammeRule(
        "helsinki-blue-economy-studio-2027",
        3,
        None,
        "Team size (1-2 founders) and an MVP are not checked; bootcamps are on site in Helsinki",
    ),
)


def instruments() -> dict[str, dict]:
    return {g["id"]: g for g in seed.load("grants")["instruments"]}


def read_date(instrument_id: str) -> str:
    """When the instrument's page was last read: its merge-log entry, else the pack's check date."""
    grants = seed.load("grants")
    for entry in grants.get("merge_log_w15b", []):
        when, _, text = entry.partition(": ")
        if text.startswith(instrument_id):
            return when
    return grants["verified_at"]


def _deadline(instrument: dict, today: date) -> date | None:
    """The deadline, only when it was read and has not passed."""
    sources = instrument.get("rule_sources", {})
    read = sources.get("deadline", sources.get("all")) in ("read", "sedia")
    deadline = date.fromisoformat(instrument["deadline"]) if instrument.get("deadline") else None
    return deadline if read and deadline and deadline >= today else None


def _is_blue(company: DemoCompany) -> bool:
    return company.vertical in BLUE_VERTICALS


def rule_decides(*, today: date | None = None) -> list[Bridge]:
    """A grant rule by registration country makes the call open to this company (SBEP call 4)."""
    today = today_or_default(today)
    bridges = []
    for instrument in instruments().values():
        tiers = instrument.get("tier_by_registration_country")
        deadline = _deadline(instrument, today)
        if not tiers or not deadline:
            continue
        for company in demo_companies():
            tier = tiers.get(company.country or "")
            registry = company.registry_evidence()
            if not (tier and tier.startswith("possible") and registry and _is_blue(company)):
                continue
            funder = instrument["participating_countries"][company.country]
            flip = f"; for comparison FI: {tiers['FI']}" if company.country != "FI" else ""
            bridges.append(
                make_bridge(
                    type="rule_decides",
                    company=company.party(),
                    counterparty=BridgeParty(name=f"{instrument['name']} via {funder}", kind="funder"),
                    reason=(
                        f"Registered in {COUNTRY_NAMES[company.country]}, where the call has a funder ({funder}): "
                        f"{tier}. The same profile registered in Finland: {tiers['FI']}"
                    ),
                    evidence_company=[registry],
                    evidence_counterparty=[
                        BridgeEvidence(
                            claim=f"{company.country}: {tier}{flip}",
                            url=instrument["url"],
                            date=read_date(instrument["id"]),
                            deadline=deadline,
                            tag=instrument["rule_sources"].get("country_rule", "read"),
                        )
                    ],
                    join="inferred",  # the funder's own eligibility rules still apply
                    deadline=deadline,
                    action=(
                        f"Check {funder}'s own rules and the theme fit, then line up partners from two other "
                        f"participating countries before the {fmt_day(deadline)} pre-proposal deadline"
                    ),
                    caveat=f"{funder}'s own eligibility rules and the thematic fit are not checked",
                )
            )
    return bridges


def proof_step(*, today: date | None = None) -> list[Bridge]:
    """A fundable validation step (test facility, access programme) for the company's technology class."""
    today = today_or_default(today)
    bridges = []
    for instrument in instruments().values():
        deadline = _deadline(instrument, today)
        patterns = [TECH_TERMS[t] for t in instrument.get("themes") or [] if t in TECH_TERMS]
        if not (instrument.get("use_as") and deadline and patterns):
            continue
        tech = re.compile(rf"\b({'|'.join(patterns)})\b", re.I)
        for company in demo_companies():
            matched = sorted({m.group(0).lower() for m in tech.finditer(company.about)})
            if not (matched and _is_blue(company)):
                continue
            bridges.append(
                make_bridge(
                    type="proof_step",
                    company=company.party(),
                    counterparty=BridgeParty(name=instrument["name"], kind="research_infrastructure"),
                    reason=(
                        f"Its technology ({', '.join(matched)}) can be validated through {instrument['name']} "
                        f"({instrument['country_rule'].lower()})"
                    ),
                    evidence_company=[company.site_evidence()],
                    evidence_counterparty=[
                        BridgeEvidence(
                            claim=instrument["amount_note"],
                            url=instrument["url"],
                            date=read_date(instrument["id"]),
                            deadline=deadline,
                            tag="read",
                        )
                    ],
                    join="inferred",
                    deadline=deadline,
                    action=f"Prepare an access request to {instrument['name']} before the {fmt_day(deadline)} cut-off",
                    caveat="Fit by technology keywords only; check which facilities take this cut-off",
                )
            )
    return bridges


def _status(instrument: dict, deadline: date | None) -> str:
    if deadline:
        return f"applications close {fmt_day(deadline)}"
    return "applications open" if instrument["status"] == "open" else "dates not published"


def programme_fit(*, today: date | None = None) -> list[Bridge]:
    """An accelerator or ecosystem programme that fits the company's stage and place now."""
    today = today_or_default(today)
    catalogue = instruments()
    bridges = []
    for rule in PROGRAMMES:
        programme = catalogue[rule.instrument_id]
        deadline = _deadline(programme, today)
        for company in demo_companies():
            age = company.age_years(today)
            in_place = rule.countries is None or company.country in rule.countries
            if age is None or age > rule.max_age_years or company.older_scaleup or not in_place:
                continue
            registry = company.registry_evidence()
            if not (_is_blue(company) and registry):
                continue
            name = programme["name"].split(" (")[0]
            topic = company.vertical_note or company.vertical.replace("_", " ")
            if EXPERT_TERMS.search(company.about):
                action = f"Invite as a mentor or expert ({topic}) for {name}"
            else:
                action = f"Point to {name} ({_status(programme, deadline)})"
            where = COUNTRY_NAMES[company.country]
            bridges.append(
                make_bridge(
                    type="programme_fit",
                    company=company.party(),
                    counterparty=BridgeParty(name=name, kind="programme"),
                    reason=f"Founded {fmt_day(company.founded)} in {where} ({topic}): fits {name} by stage and place",
                    evidence_company=[registry, company.site_evidence()],
                    evidence_counterparty=[
                        BridgeEvidence(
                            claim=programme["deadline_note"].split(". ")[0],
                            url=programme["url"],
                            date=read_date(programme["id"]),
                            deadline=deadline,
                            tag="read",
                        )
                    ],
                    join="inferred",
                    deadline=deadline,
                    action=action,
                    caveat=f"{rule.unchecked}; fit by stage, place and vertical",
                    mode="apelago",
                )
            )
    return bridges
