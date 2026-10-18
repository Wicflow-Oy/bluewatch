"""Idea Harbour applies the scout's minors rule: no team from a youth or school event becomes a public lead."""

from __future__ import annotations

import pytest

from bluewatch import seed
from bluewatch.bridges.common import slug
from bluewatch.ideas import public_reads
from bluewatch.ideas.pipeline import public_ideas
from bluewatch.scout.projects import is_youth_or_school
from tests.ideas.helpers import SESSION


def excluded_lead_ids() -> set[str]:
    rows = seed.load("hackathon_projects")["projects"]
    return {f"hackathon:{slug(r['event'])}/{slug(r['team_or_project'])}" for r in rows if is_youth_or_school(r)}


def test_the_seed_has_youth_events_to_leave_out():
    excluded = excluded_lead_ids()
    assert any("green-warriors" in lead for lead in excluded)  # TOMI (team Green Warriors), YDCC 2025


def test_no_public_lead_or_recorded_read_comes_from_a_youth_or_school_event(today):
    excluded = excluded_lead_ids()
    assert not {p.id for p in public_ideas("blue", today)} & excluded
    assert not {p.id for p in public_ideas("climate_circular", today)} & excluded
    assert not set(public_reads.recorded()["reads"]) & excluded


@pytest.mark.parametrize("mode", ["apelago", "redstone"])
@pytest.mark.parametrize("preset", ["blue", "climate_circular"])
def test_the_review_queue_never_lists_them(client, mode, preset):
    res = client.get(f"/api/ideas/queue?mode={mode}&preset={preset}", headers={"X-Demo-Session": SESSION})
    assert res.status_code == 200
    assert not {item["id"] for item in res.json()["items"]} & excluded_lead_ids()
    assert "Green Warriors" not in res.text
