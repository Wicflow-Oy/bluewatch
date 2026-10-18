"""Bridges from public research projects (CORDIS, Interreg): already works with them, lab window."""

from __future__ import annotations

from datetime import date, timedelta

from bluewatch import seed
from bluewatch.bridges.common import fmt_day, fmt_month, make_bridge, today_or_default
from bluewatch.bridges.companies import by_registry_id
from bluewatch.bridges.generators.funding import instruments, read_date
from bluewatch.models import Bridge, BridgeEvidence, BridgeParty

# Project participant names (as CORDIS or the programme site prints them) -> partners.json ids.
# Only the same legal entity, or its national subsidiary for the groups listed in GROUP_LEVEL.
PARTNER_ALIASES = {
    "FINTRAFFIC MERILIIKENTEENOHJAUS OY": "fintraffic",
    "FINNLINES OYJ": "finnlines",
    "SUOMEN YMPARISTOKESKUS": "syke",
    "TEKNOLOGIAN TUTKIMUSKESKUS VTT OY": "vtt",
    "ABO AKADEMI": "abo_akademi",
    "MEYER TURKU OY": "meyer_turku",
    "HELSINGIN SATAMA OY": "port_of_helsinki",
    "ILMATIETEEN LAITOS": "fmi",
    "TURUN YLIOPISTO": "university_of_turku",
    "University of Turku": "university_of_turku",
    "AB YRKESHOGSKOLAN VID ABO AKADEMI": "novia_uas",
    "NESTE OYJ": "neste",
    "WARTSILA FINLAND OY": "wartsila",
    "KONGSBERG MARITIME FINLAND OY": "kongsberg_maritime",
}
GROUP_LEVEL = {"WARTSILA FINLAND OY", "KONGSBERG MARITIME FINLAND OY"}
CUSTOMER_TYPES = {"corporate", "shipowner", "port", "public_buyer"}
RESEARCH_TYPES = {"REC", "HES"}
LAB_WINDOW = timedelta(days=730)  # "nearing its end": ends within two years
TIER_FIT = {"Strong": 1.0, "Medium": 0.7, "Low": 0.4}


def _partners() -> dict[str, dict]:
    return {p["id"]: p for p in seed.load("partners")["entities"]}


def _projects(today: date) -> list[dict]:
    """Running projects (end date not passed), with every participant role we hold."""
    rows = seed.load("research_prestartup")["projects"]
    return [p for p in rows if p["end"] and date.fromisoformat(p["end"]) >= today]


def _url(project: dict) -> str | None:
    return project.get("cordis_url") or project.get("source_url")


def _tag(project: dict) -> str:
    return "cordis" if project.get("cordis_url") else "read"


def _programme(project: dict) -> str:
    return "Interreg" if "Interreg" in project["funding_scheme"] else "EU"


def already_works_with(*, today: date | None = None) -> list[Bridge]:
    """A demo company and a known partner take part in the same running project."""
    today = today_or_default(today)
    partners = _partners()
    bridges = []
    for project in _projects(today):
        ids = {c["name"]: c["businessId"] for c in project.get("company_age_check_prh", [])}
        for member in project["finnish_participants"]:
            company = by_registry_id(ids.get(member["name"]))
            if not company:
                continue
            others = [p for p in project["finnish_participants"] if p["name"] in PARTNER_ALIASES and p is not member]
            customers = [p for p in others if partners[PARTNER_ALIASES[p["name"]]]["type"] in CUSTOMER_TYPES]
            chosen = customers or others
            if not chosen:
                continue
            names = "; ".join(partners[PARTNER_ALIASES[p["name"]]]["name"] for p in chosen)
            weak = [p for p in chosen if p["role"] == "thirdParty" or p["name"] in GROUP_LEVEL]
            end = date.fromisoformat(project["end"])
            dated = {"url": _url(project), "date": project["start"], "end": end, "tag": _tag(project)}
            coordinator = project["coordinator"]
            caveats = ["Co-participation is not a purchase"] + (
                ["a linked third party or a national subsidiary, not the named group itself"] if weak else []
            )
            bridges.append(
                make_bridge(
                    type="already_works_with",
                    company=company.party(),
                    counterparty=BridgeParty(
                        name=names,
                        kind="+".join(sorted({partners[PARTNER_ALIASES[p["name"]]]["type"] for p in chosen})),
                    ),
                    reason=(
                        f"Co-participants in the {_programme(project)} project {project['acronym']}, "
                        f"which runs to {fmt_month(end)}"
                    ),
                    evidence_company=[
                        BridgeEvidence(
                            claim=(
                                f"{company.name} is a {member['role']} in {project['acronym']} "
                                f"(coordinated by {coordinator['name']}, {coordinator['country']})"
                            ),
                            **dated,
                        )
                    ],
                    evidence_counterparty=[
                        BridgeEvidence(
                            claim="; ".join(f"{p['name']} ({p['role']})" for p in chosen) + " in the same project",
                            **dated,
                        )
                    ],
                    join="partial" if weak else "exact",
                    action=(
                        "Ask for a pilot or reference-customer conversation inside the existing project relationship"
                        if customers
                        else "Use the project partners as pilot and validation references"
                    ),
                    caveat="; ".join(caveats),
                    identifying_terms=[project["acronym"], coordinator["name"]],  # the project page lists the company
                )
            )
    return bridges


def _research_members(project: dict) -> list[dict]:
    members = [p for p in project["finnish_participants"] if p["type"] in RESEARCH_TYPES]
    return sorted(members, key=lambda p: p["role"] not in ("coordinator", "lead partner"))


def _display(name: str) -> str:
    alias = PARTNER_ALIASES.get(name)
    return _partners()[alias]["name"] if alias else name  # as the project register prints it


def lab_window(*, today: date | None = None) -> list[Bridge]:
    """A running research project ends within two years and no young company takes part yet."""
    today = today_or_default(today)
    lab2impact = instruments()["apelago-lab2impact-2027"]
    programme = BridgeParty(name=lab2impact["name"], kind="programme")
    offer = BridgeEvidence(
        claim=f"{lab2impact['name']}: for researchers becoming founders; {lab2impact['deadline_note'].split('. ')[0]}",
        url=lab2impact["w11_sources"][0],
        date=read_date(lab2impact["id"]),
        tag="read",
    )
    bridges = []
    for project in _projects(today):
        end = date.fromisoformat(project["end"])
        has_young_company = any(c["young_within_10_years"] for c in project.get("company_age_check_prh", []))
        members = _research_members(project)
        if end - today > LAB_WINDOW or has_young_company or not members:
            continue
        lead = members[0]
        team = BridgeParty(
            name=f"{project['acronym']} team, {_display(lead['name'])} (research output)",
            kind="research_group",
            country="FI",
        )
        bridges.append(
            make_bridge(
                type="lab_window",
                company=team,
                counterparty=programme,
                reason=(
                    f"{project['acronym']} ({_programme(project)}) ends {fmt_day(end)} and no young company "
                    f"takes part: a spin-out window for the research team"
                ),
                evidence_company=[
                    BridgeEvidence(
                        claim=(
                            f"{_display(lead['name'])} is {lead['role']}; runs "
                            f"{fmt_day(date.fromisoformat(project['start']))} to {fmt_day(end)}"
                        ),
                        url=_url(project),
                        date=project["start"],
                        end=end,
                        tag=_tag(project),
                    )
                ],
                evidence_counterparty=[offer],
                join="inferred",
                deadline=end,
                action=(
                    f"Invite the {project['acronym']} team through A'Pelago's Lab2Impact channel before the "
                    f"project ends ({fmt_day(end)}); group level, no individuals"
                ),
                caveat="No company exists yet; rights to the results are unknown",
                mode="apelago",
                identifying_terms=[project["acronym"], _display(lead["name"]), lead["name"]],
                fit=TIER_FIT.get(project["tier"], 0.4),
            )
        )
    return bridges
