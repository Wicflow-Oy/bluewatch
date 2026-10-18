"""EU research projects: CORDIS project records, from a recorded pull of CORDIS's own JSON export.

Each project becomes an eu_project signal with its dates and participants. Finnish participants come from the
export; their organisation types (PRC company, HES university, REC research body) and PRH business IDs come from
the verified demo pack where it has them.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from bluewatch import seed
from bluewatch.config import settings
from bluewatch.models import EntityRef, Signal
from bluewatch.sources.common import FIXTURES, fixture_time, make_signal, parse_date

SOURCE = "cordis"
EXPORT = FIXTURES / "w15_cordis_repull.json"
ALL_ROLES = "sources/w15_cordis_fi_all_roles.json"


def _status(start, end) -> str:
    today = settings().today
    if start and start > today:
        return "not started"
    return "ended" if end and end < today else "running"


def _participants(project: dict, demo: dict, third_parties: list[list[str]]) -> list[dict]:
    types = {p["name"]: p.get("type") for p in demo.get("finnish_participants") or []}
    ids = {c["name"]: c.get("businessId") for c in demo.get("company_age_check_prh") or []}
    rows = [
        {
            "name": p["name"],
            "role": p.get("role"),
            "country": "FI",
            "ec_contribution_eur": p.get("ec_contribution_eur"),
            "type": types.get(p["name"]),
            "business_id": ids.get(p["name"]),
        }
        for p in project.get("finnish_participants") or []
    ]
    named = {p["name"] for p in rows}
    rows += [{"name": name, "role": role, "country": "FI"} for name, role in third_parties if name not in named]
    return rows


def project_signal(project: dict, demo: dict, third_parties: list[list[str]], seen_at: datetime) -> Signal:
    start, end = parse_date(project.get("start")), parse_date(project.get("end"))
    signed = parse_date(project.get("ec_signature_date"))
    gid = project["grant_agreement_id"]
    url = f"https://cordis.europa.eu/project/id/{gid}"
    payload = {
        "grant_agreement_id": gid,
        "acronym": project.get("acronym"),
        "start": project.get("start"),
        "end": project.get("end"),
        "ec_signature_date": project.get("ec_signature_date"),
        "status": _status(start, end),
        "cordis_status": project.get("cordis_status"),
        "ec_max_contribution_eur": project.get("ec_max_contribution_eur"),
        "coordinator": project.get("coordinator"),
        "participants": _participants(project, demo, third_parties),
        "call": demo.get("call"),
        "funding_scheme": demo.get("funding_scheme"),
        "cordis_last_update": project.get("cordis_last_update"),
    }
    return make_signal(
        SOURCE,
        "eu_project",
        EntityRef(project_url=url, name=project.get("acronym")),
        key=gid,
        event_date=signed or start,
        first_seen_at=seen_at,
        url=url,
        title=f"{project.get('acronym')}: {project.get('title')}",
        payload=payload,
    )


def load_projects(path: Path | None = None) -> list[Signal]:
    """Horizon projects with Finnish participants (ocean, maritime, water), dated by the EC signature."""
    data = json.loads(Path(path or EXPORT).read_text(encoding="utf-8"))
    seen_at = fixture_time(f"{data['checked']}T12:03:13+03:00") if "checked" in data else datetime.now()
    demo = {p["grant_agreement_id"]: p for p in seed.load("research_prestartup")["projects"]}
    roles = seed.fixture(ALL_ROLES)
    projects = [
        p
        for p in data.get("projects", []) + data.get("extras", [])
        if p.get("grant_agreement_id") and not p.get("error")
    ]
    return [
        project_signal(p, demo.get(p["grant_agreement_id"], {}), roles.get(p.get("acronym"), []), seen_at)
        for p in projects
    ]
