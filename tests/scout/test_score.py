from datetime import date

import pytest

from bluewatch import seed
from bluewatch.models import HackathonProject
from bluewatch.scout.projects import load_projects
from bluewatch.scout.score import event_date, placement_class, promise_score, theme_fit

SEED_PLANS = {p["id"]: p for p in seed.load("hackathon_scout")["contact_plans"]}


def _team(name: str) -> HackathonProject:
    return next(p for p in load_projects() if p.team_or_project == name)


@pytest.mark.parametrize(("plan_id", "team", "total"), [("S1", "KU.exe", 87), ("S2", "NOMAD", 77)])
def test_seed_scores_reproduced_part_by_part(plan_id, team, total, today):
    score = promise_score(_team(team), today=today)
    assert score.total == total
    shown = {k: v for k, v in score.parts.items() if v}
    assert shown == SEED_PLANS[plan_id]["promise_score"]["parts"]


def test_every_part_has_a_ceiling_and_the_ceilings_make_100(today):
    score = promise_score(_team("KU.exe"), today=today)
    assert score.maxima.keys() == score.parts.keys() and sum(score.maxima.values()) == 100
    assert all(score.parts[k] <= score.maxima[k] for k in score.parts)


def test_theme_fit_rubric():
    assert theme_fit(_team("KU.exe")) == 18  # blue core, challenge owner, two verticals
    assert theme_fit(_team("NOMAD")) == 15  # the same, minus 3 for a defence-leaning idea


def _project(**fields) -> HackathonProject:
    return HackathonProject(id="x", event="E", team_or_project="T", **fields)


@pytest.mark.parametrize(
    ("placement", "expected"),
    [
        ("1st (winner)", "1st"),
        ("Champion (MPA challenge)", "1st"),
        ("1st runner-up (ONE challenge)", "2nd"),
        ("2nd runner-up (ONE challenge)", "3rd"),
        ("3rd (shared)", "3rd"),
        ("Finalist (top 8)", "finalist_or_award"),
        ("Semi-finalist", "listed"),
        ("Finalist (not among the three winners)", "finalist_or_award"),
        ("2025 challenge/project listed in the press kit; not the local winner; team outcome not published", "listed"),
        ("Selected participant (no award)", "listed"),
        ("Local winner; International Grand Finale finalist, rank not published", "1st"),
    ],
)
def test_placement_classes(placement, expected):
    assert placement_class(_project(placement=placement)) == expected


def test_dates_use_the_latest_passed_date_or_stay_unknown(today):
    assert event_date(_project(date="2026-09-25/2026-09-27"), today) == date(2026, 9, 27)
    assert event_date(_project(date="Finalists announced 2026-10-15; ceremony 2026-11-12"), today) == date(2026, 10, 15)
    assert event_date(_project(date="Oct 2025 (exact day not stated)"), today) == date(2025, 10, 1)
    assert event_date(_project(date="2026 (date not retrieved)"), today) is None
    assert promise_score(_project(date="not stated"), today=today).parts["recency"] == 0


def test_a_team_listed_as_not_the_winner_ranks_below_the_local_winners(today):
    """A press-kit row that says "not the local winner" scores as listed, never as a winner."""
    press_kit = [p for p in load_projects() if "not the local winner" in (p.placement or "")]
    winners = [p for p in load_projects() if (p.placement or "").startswith("Local winner")]
    assert press_kit and winners
    best_listed = max(promise_score(p, today=today).parts["placement"] for p in press_kit)
    assert best_listed < min(promise_score(p, today=today).parts["placement"] for p in winners)
