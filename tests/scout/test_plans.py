import re

from bluewatch.models import ContactPlan
from bluewatch.scout.plans import PERSONAL, gaps, plans, public_project, public_url, team_phrase
from bluewatch.scout.projects import load_projects


def _plan(team: str, top: list[ContactPlan]) -> ContactPlan:
    project_id = next(p.id for p in load_projects() if p.team_or_project == team)
    return next(p for p in top if p.project_id == project_id)


def test_ku_exe_tops_the_list_and_nomad_follows(today):
    top = plans(20, today=today)
    assert len(top) == 20
    assert [p.promise_score.total for p in top[:2]] == [87, 77]
    assert top[0].project_id == "portathon-2026/ku-exe"


def test_s1_plan_routes_to_the_organiser_first(today):
    plan = _plan("KU.exe", plans(20, today=today))
    assert [r.kind for r in plan.route_ladder] == [
        "organiser",
        "university_office",
        "team_public_channel",
        "event",
        "opt_in",
    ]
    assert plan.route_ladder[0].organisation == "Klaipeda Science and Technology Park"
    assert plan.route_ladder[0].contact_page_url.startswith("https://kmtp.lt/")
    assert plan.draft.to_route_rank == 1
    assert "Northern Blue 2027" in plan.offer
    assert plan.questions[0] == "Are you continuing KU.exe after PORTATHON 2026?"  # not the hedged solution name
    assert "Has the Port of La Rochelle, or another buyer, shown interest in a pilot?" in plan.questions


def test_the_redstone_workspace_offers_its_own_first_call_not_a_programme(today):
    redstone = _plan("KU.exe", plans(20, today=today, mode="redstone"))
    assert redstone.offer == "A first call with Redstone about building a company from the project"
    assert "A'Pelago" not in redstone.model_dump_json()
    assert redstone.draft.subject == "PORTATHON 2026 winner KU.exe: a first call with Redstone and three questions"


def test_s2_plan_uses_the_warm_route_and_flags_dual_use(today):
    plan = _plan("NOMAD", plans(20, today=today))
    assert plan.route_ladder[0].kind == "warm_intro" and plan.route_ladder[0].organisation.startswith("Redstone")
    assert plan.route_ladder[1].kind == "organiser"
    assert plan.draft.to_route_rank == 2  # the draft goes to an organisation inbox, not to the juror
    assert "Redstone" in plan.offer
    assert "Defence buyers, civil uses, or both?" in plan.questions
    assert any(f.startswith("Dual use") for f in plan.flags)


def test_gaps_are_unknowns_linked_to_their_questions(today):
    plan = plans(1, today=today)[0]
    asked = [g for g in plan.gaps if g.next_check.kind == "ask_founder"]
    assert [g.next_check.question for g in asked] == plan.questions
    assert all(g.state == "unknown" and g.project_id == plan.project_id for g in plan.gaps)
    assert len(plan.draft.points) == 5 and "Three questions" in plan.draft.points[2]


def test_plans_are_organisation_level_only(today):
    for plan in plans(40, today=today):
        assert "@" not in plan.model_dump_json()
        assert plan.route_ladder[-1].kind == "opt_in"
        for route in plan.route_ladder:
            assert route.contact_page_url is None or not PERSONAL.search(route.contact_page_url)
        assert plan.flags[0].startswith("Plan only")  # sending belongs to the outreach desk


def test_companies_are_left_to_the_company_pipeline(today):
    companies = {p.id for p in load_projects() if p.company_status == "already_a_company"}
    assert not companies & {p.project_id for p in plans(200, today=today)}


def test_personal_and_code_host_pages_are_never_used():
    assert public_url("https://github.com/oceanhackweek/ohw26_proj") is None
    assert public_url("mailto:team@example.org") is None
    assert public_url("https://www.linkedin.com/in/someone") is None
    assert public_url("https://kmtp.lt/results/ ; https://other.example/") == "https://kmtp.lt/results/"
    assert public_url("not recorded (search snippet of a personal LinkedIn post)") is None  # a note, not a page
    assert not re.search(r"name|email|phone", " ".join(ContactPlan.model_fields))


def test_public_project_drops_research_asides(today):
    by_team = {p.team_or_project: p for p in load_projects()}
    hult = public_project(by_team["Flow Guard Solutions (KAUST, Saudi Arabia)"], today=today)
    assert hult.team_or_project == "Flow Guard Solutions"  # named as Idea Harbour names it
    assert hult.city is None and hult.country_code is None and not hult.online
    assert "meta" not in hult.model_dump()


def test_public_project_serves_structured_facts_the_interface_can_translate(today):
    """Placement is a class, the country an ISO code and online a flag: no English research note is served."""
    by_team = {p.team_or_project: p for p in load_projects()}
    whalze = public_project(by_team["Whalze"], today=today)
    assert (whalze.placement, whalze.city, whalze.country_code) == ("1st", "Toulon", "FR")
    online = public_project(by_team["RugOBSS - Invasive Macroalgae Observing Beachcast System"], today=today)
    assert online.online and online.city is None and online.country_code is None
    served = [plan.project for plan in plans(200, today=today)]
    assert not any(p.team_or_project.startswith("[") for p in served)  # press-kit codes stay in the seed
    assert not any(re.search(r"\((?:listed by|no short|informal name)", p.team_or_project) for p in served)
    assert not any(re.search(r"research note|\.md\b|unverified|surfaced in search", p.idea or "") for p in served)


def test_network_hosts_are_named_without_the_local_label(today):
    for plan in plans(200, today=today):
        assert not any(r.organisation.startswith("local:") for r in plan.route_ladder)


def test_a_team_the_organiser_left_unnamed_is_asked_about_the_project_not_a_description(today):
    unnamed = next(p for p in load_projects() if p.team_or_project.startswith("Unnamed winning team"))
    assert team_phrase(unnamed) == "the winning team"
    assert gaps(unnamed, today=today)[0].next_check.question.startswith("Are you continuing the project after ")
    ku = next(p for p in load_projects() if p.team_or_project == "KU.exe")
    assert team_phrase(ku) == "the KU.exe team"
