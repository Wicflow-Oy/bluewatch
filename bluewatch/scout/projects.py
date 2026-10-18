"""Hackathon projects from the seed, at project level only. Youth and school events are left out."""

from __future__ import annotations

import re
from functools import lru_cache

from bluewatch import seed
from bluewatch.bridges.common import norm_name, slug
from bluewatch.models import HackathonProject

# Words for minors and their schools; "kids" also inside a name ("OffshoreWind4Kids"). A school for adults
# ("Business School", "School of Aquatic Sciences") and a university college are no sign.
YOUTH_OR_SCHOOL = re.compile(
    r"\b(junior|young|youths?|high[- ]school|secondary school|primary school|pupils?|teen(?:ager)?s?|k-12|under[- ]18"
    r"|lukio|schools|school ?(?:children|kids|students|teams?)|vocational)\b|(?<![a-z])kids?\b",
    re.I,
)


def is_youth_or_school(row: dict) -> bool:
    """Any sign of a youth or school event leaves the project out, even when an age range says adults: the
    age claim covers the event, not each team, and a public demo must not reach out to minors. The source URL
    counts too, because it often carries the organiser's own headline ("singapore-youths-propose-..."), and so
    does the team's name. A "young innovators" event that states no age limit is left out on the same grounds,
    and so is every team at an event run by a kids' organisation, whose college teams may be vocational
    students under 18."""
    if row.get("minors_likely"):
        return True
    fields = ("event", "edition", "organiser", "theme", "team_type", "source_url", "team_or_project")
    text = " ".join(str(row.get(k) or "") for k in fields)
    return bool(YOUTH_OR_SCHOOL.search(text))


@lru_cache(maxsize=1)
def verified_plans() -> dict[tuple[str, str], dict]:
    """The contact plans the lead checked on the organisers' pages, keyed by (event, team)."""
    plans = seed.load("hackathon_scout")["contact_plans"]
    return {(norm_name(p["project"]["event"]), norm_name(p["project"]["team_or_project"])): p for p in plans}


def _verified_facts(row: dict) -> dict:
    """Facts from a verified plan (team count, jury, institution, organiser support) for this row."""
    plan = verified_plans().get((norm_name(row["event"]), norm_name(row["team_or_project"])))
    if not plan:
        return {}
    organiser_route = next((r for r in plan["route_ladder"] if r["kind"] == "organiser"), {})
    return {
        "plan_id": plan["id"],
        "placement": plan["project"]["placement"],
        "organiser": plan["project"]["organiser"],
        "institution": plan["project"].get("institution"),
        "solution_name": plan["project"].get("solution_name"),
        "organiser_note": organiser_route.get("why"),
        "organiser_how": organiser_route.get("how"),
        "organiser_page": organiser_route.get("contact_page_url"),
        "source_url": plan["project"]["source_url"],
    }


def _project(row: dict) -> HackathonProject:
    return HackathonProject(
        id=f"{slug(row['event'])}/{slug(row['team_or_project'])}",
        event=row["event"],
        edition=row.get("edition"),
        date=row.get("date"),
        city=row.get("city"),
        country=row.get("country"),
        organiser=row.get("organiser"),
        placement=row.get("placement"),
        team_or_project=row["team_or_project"],
        idea=row.get("idea"),
        source_url=row.get("source_url"),
        tag=row.get("tag"),
        company_status=row.get("company_status") or "check",
        minors_likely=bool(row.get("minors_likely")),
        in_window=row.get("in_window") is not False,  # undated rows stay in, as in the seed's own count
        meta={
            "theme": row.get("theme"),
            "country_code": row.get("country_code"),
            "kind": row.get("kind"),
            "team_type": row.get("team_type"),
            "later_company": row.get("later_company"),
            "verified": _verified_facts(row),
        },
    )


@lru_cache(maxsize=1)
def _load() -> tuple[HackathonProject, ...]:
    rows = seed.load("hackathon_projects")["projects"]
    return tuple(_project(r) for r in rows if not is_youth_or_school(r))


def load_projects() -> list[HackathonProject]:
    return list(_load())
