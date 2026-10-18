from bluewatch.scout.projects import is_youth_or_school, load_projects


def test_loads_the_seed_minus_youth_events():
    projects = load_projects()
    # 217 in the seed, minus Ocean Youth Challenge, the three YDCC teams, the 20 MaritimeONE 2025 teams, the
    # Young Innovators Challenge winner (no age limit stated) and the 12 Floating Wind Challenge 2026 teams
    # (run by OffshoreWind4Kids, with a Dutch vocational college team)
    assert len(projects) == 180
    assert len({p.id for p in projects}) == len(projects)
    assert not any(p.minors_likely for p in projects)
    assert "Ocean Youth Challenge pitching event" not in {p.event for p in projects}


def test_youth_and_school_events_are_excluded():
    assert is_youth_or_school({"event": "Stockholm Junior Water Prize"})
    assert is_youth_or_school({"event": "Blue hack", "theme": "for high-school pupils"})
    assert is_youth_or_school({"event": "Any", "minors_likely": True})
    assert is_youth_or_school({"event": "Youth Digital Citizen Challenge", "theme": "youth aged 18-30"})
    assert is_youth_or_school({"event": "Young Innovators Challenge 2026 (Marine Insight Virtual Summit)"})
    assert not is_youth_or_school({"event": "Hult Prize", "organiser": "Hult International Business School"})


def test_kids_school_and_vocational_signals_count_wherever_they_appear():
    windmasters = {
        "event": "Floating Wind Challenge 2026 (Offshore Wind Challenge, 5th edition)",
        "organiser": "OffshoreWind4Kids vzw (Belgian non-profit initiative; sponsor list not read)",
        "team_or_project": "MyTec Ocean Windmasters 2026 (Nova College Beverwijk, Netherlands)",
    }
    assert is_youth_or_school(windmasters)
    assert not any(p.event == windmasters["event"] for p in load_projects())
    assert is_youth_or_school({"event": "Blue hack", "theme": "open to schools and universities"})
    assert is_youth_or_school({"event": "Blue hack", "team_or_project": "Harbour school team"})
    assert is_youth_or_school({"event": "Blue hack", "team_type": "vocational college students"})
    for adults in (
        "Trinity Floating Wind Team (Trinity College Dublin, Ireland)",
        "The Shark team (IFP School, France)",
    ):
        assert not is_youth_or_school({"event": "Blue hack", "team_or_project": adults})
    assert not is_youth_or_school({"event": "Fish hackweek", "organiser": "UW School of Aquatic and Fishery Sciences"})


def test_the_organisers_own_headline_counts_as_a_youth_signal():
    url = "https://www.smf.com.sg/singapore-youths-propose-innovative-ways-to-address-maritime-challenges/"
    assert is_youth_or_school({"event": "MaritimeONE Case Summit 2025", "source_url": url})
    assert not any(p.event.startswith("MaritimeONE Case Summit 2025") for p in load_projects())


def test_verified_plan_facts_are_attached():
    by_team = {p.team_or_project: p for p in load_projects()}
    assert by_team["KU.exe"].meta["verified"]["plan_id"] == "S1"
    assert by_team["NOMAD"].meta["verified"]["plan_id"] == "S2"  # matched across "Häkk" / "Hakk"
