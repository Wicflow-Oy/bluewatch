from datetime import date

import pytest

from bluewatch import seed
from bluewatch.bridges.generators import (
    GENERATORS,
    already_works_with,
    lab_window,
    law_creates_buyer,
    programme_fit,
    proof_step,
    rule_decides,
    won_before_open_again,
)
from bluewatch.bridges.generators.procurement import title_terms

TED = "https://ted.europa.eu/en/notice/-/detail/"


def _for(bridges, registry_id):
    return [b for b in bridges if b.company.registry_id == registry_id]


def test_b1_alpo_to_sansia_reproduced_from_the_ted_fixtures(today):
    sansia = [b for b in _for(won_before_open_again(today=today), "3101791-3") if b.counterparty.name == "Sansia Oy"]
    assert len(sansia) == 1
    bridge = sansia[0]
    assert bridge.confidence == "verified"
    assert bridge.deadline == date(2026, 10, 30)
    assert {e.url for e in bridge.evidence_counterparty} == {TED + "668013-2026", TED + "713640-2026"}
    assert [e.url for e in bridge.evidence_company] == [TED + "423989-2026"]
    assert bridge.anonymised_name == "A Rauma boat builder"


def test_b2_hansel_is_probable_because_only_the_cpv_class_matches(today):
    hansel = [b for b in _for(won_before_open_again(today=today), "3101791-3") if b.counterparty.name == "Hansel Oy"]
    assert hansel[0].confidence == "probable"
    assert {TED + "681017-2026", TED + "681402-2026"} <= {e.url for e in hansel[0].evidence_counterparty}
    assert "Lot fit not checked" in hansel[0].caveat


def test_class_codes_survive_finnish_inflection():
    award = title_terms("TP1/26EU Öljyntorjunta-alukset C-luokka")
    assert award & title_terms("C-luokan öljyntorjunta- ja pelastusalus") == {"class c", "öljyn"}


def test_closed_tenders_make_no_bridge():
    assert won_before_open_again(today=date(2026, 11, 10)) == []


def test_b6_sbep_country_rule_reproduced(today):
    zeabuz = _for(rule_decides(today=today), "924571179")
    assert len(zeabuz) == 1
    bridge = zeabuz[0]
    assert bridge.confidence == "possible"
    assert bridge.deadline == date(2026, 11, 16)
    assert "SBEP" in bridge.counterparty.name and "Research Council of Norway" in bridge.counterparty.name
    claim = bridge.evidence_counterparty[0].claim
    assert "possible: funder's own eligibility rules apply" in claim and "excluded: no Finnish funder" in claim
    assert bridge.evidence_company[0].tag == "registry"


def test_the_rule_excludes_finnish_companies(today):
    assert not [b for b in rule_decides(today=today) if b.company.country == "FI"]


def test_co_participants_in_mission_reproduce_b3(today):
    awake = {b.counterparty.name: b for b in _for(already_works_with(today=today), "2945733-8")}
    mission = awake["Fintraffic (Vessel Traffic Services); Finnlines"]
    assert mission.confidence == "verified"
    assert mission.caveat.startswith("Co-participation is not a purchase")
    assert awake["Kongsberg Maritime"].confidence == "probable"  # a linked third party in SEAMLESS


def test_lab_windows_skip_projects_that_already_have_a_young_company(today):
    windows = {b.company.name.split(" team")[0]: b for b in lab_window(today=today)}
    assert windows["CirclesOfLife"].deadline == date(2026, 12, 31)
    assert "MISSION" not in windows and "AlgaePro BANOS" not in windows
    assert all(b.counterparty.name == "A'Pelago Lab2Impact 2027" for b in windows.values())


def test_regulation_comes_from_the_seed_and_names_a_real_buyer(today):
    (bridge,) = law_creates_buyer(today=today)
    assert bridge.company.registry_id == "3134791-2"
    assert bridge.counterparty.name == "Port of Helsinki (Helsingin Satama Oy)"
    assert bridge.deadline == date(2030, 1, 1)
    assert bridge.confidence == "probable"
    assert bridge.evidence_counterparty[0].url == "https://eur-lex.europa.eu/eli/reg/2023/1805/oj"


def test_proof_step_matches_sensor_ventures_to_emso(today):
    bridges = {b.company.name: b for b in proof_step(today=today)}
    assert bridges["Sensemakers ApS"].counterparty.name == "EMSO ERIC Physical Access 2026"
    assert bridges["Sensemakers ApS"].deadline == date(2026, 10, 31)
    assert "Marine Charging Point" not in bridges  # "safety monitoring" is not a sensing product


def test_programme_fit_invites_a_consultancy_as_an_expert(today):
    meriva = {b.counterparty.name: b for b in _for(programme_fit(today=today), "3652359-1")}
    assert meriva["A'Pelago Northern Blue 2027"].action == (
        "Invite as a mentor or expert (aquaculture) for A'Pelago Northern Blue 2027"
    )
    assert meriva["Helsinki Blue Economy Studio"].deadline == date(2026, 11, 30)
    assert meriva["Helsinki Blue Economy Studio"].reason.startswith("Founded 3 Sep 2026 in Finland (")  # not ISO


def _known_counterparties() -> set[str]:
    tenders = seed.fixture("sources/ted_open_tenders_blue_nordic_baltic.json")["open"]
    partners = seed.load("partners")["entities"]
    grants = seed.load("grants")["instruments"]
    return {t["buyer"] for t in tenders} | {p["name"] for p in partners} | {g["name"] for g in grants}


@pytest.mark.parametrize("generator", GENERATORS, ids=lambda g: g.__name__)
def test_every_generated_bridge_follows_the_rules(generator, today):
    known = _known_counterparties()
    bridges = generator(today=today)
    assert bridges, "each generator produces at least one bridge on the recorded data"
    for bridge in bridges:
        assert bridge.type == bridge.generator == generator.__name__
        assert bridge.evidence_company and bridge.evidence_counterparty
        assert bridge.deadline is None or bridge.deadline >= today
        assert bridge.action and bridge.confidence in ("verified", "probable", "possible")
        # Never invent a counterparty: every named part comes from the recorded data.
        names = bridge.counterparty.name.split("; ")
        assert all(any(k in n or n in k for k in known) for n in names), bridge.counterparty.name
