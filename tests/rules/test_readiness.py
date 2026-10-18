from datetime import date

from bluewatch.rules.readiness import assess_levels
from tests.rules.helpers import company, ev, registered


def levels(*evidence):
    return {lv.key: lv for lv in assess_levels(company(), list(evidence), preset="blue")}


def test_unknown_is_none_never_zero():
    lv = levels(ev("Harbour software for marinas."))
    trl = lv["trl"]
    assert trl.level is None and trl.applicable
    assert trl.unknown_reason and trl.raise_by
    assert lv["irl"].level is None and lv["irl"].unknown_reason  # no register fact, no milestone


def test_service_company_has_no_trl():
    trl = levels(ev("Aquaculture consulting, project planning, training and R&D"))["trl"]
    assert trl.applicable is False
    assert trl.level is None
    assert "Service company" in trl.unknown_reason


def test_stated_not_applicable_wins():
    stated = ev("TRL: not applicable", field="trl", state="not_applicable", why_unknown="Service company")
    assert levels(stated)["trl"].applicable is False


def test_trl_cues_follow_the_scale():
    assert levels(ev("38 Rotor Sails installed on 21 vessels"))["trl"].level == 9
    assert levels(ev("A pilot of 20 m3/day is under test with Adazu udens"))["trl"].level == 7
    assert levels(ev("Tunicates caught for a demo with a potential customer"))["trl"].level == 6
    assert levels(ev("Prototype tested in the lab"))["trl"].level == 4


def test_public_contract_award_means_commercial_delivery_and_test_sale():
    award = ev(
        "Public contract award: oil-spill vessels (buyer: Region A)", field="public_contracts", tag="ted", family="ted"
    )
    lv = levels(ev("Aluminium boats for rescue work."), award)
    assert lv["trl"].level == 8
    assert lv["brl"].level == 6
    second = ev(
        "Public contract award: workboats (buyer: Border Guard)", field="public_contracts", tag="ted", family="ted"
    )
    assert levels(ev("Aluminium boats."), award, second)["brl"].level == 7  # two buyers: repeat demand


def test_none_found_is_not_an_award():
    nothing = ev("No TED award found by business ID", field="public_contracts", tag="ted", value="none_found")
    assert levels(ev("Boats."), nothing)["brl"].level == 2


def test_brl_starts_at_a_described_offer_and_rises_with_pricing():
    assert levels(ev("Fishing analytics app."))["brl"].level == 2
    assert levels(ev("Analytics app; subscription with a 14-day trial"))["brl"].level == 4
    assert levels()["brl"].level is None


def test_irl_milestones():
    assert levels(registered())["irl"].level == 3
    assert levels(registered(), ev("A'Pelago Nordic Blue 2026 batch member", field="programme"))["irl"].level == 4
    share = ev(
        "Share issue registered 20 Aug 2026 (PRH trade register; amount not public)",
        field="funding",
        tag="registry",
        family="prh_notices",
        event_date=date(2026, 8, 20),
    )
    assert levels(registered(), share)["irl"].level == 6


def test_snippets_never_set_a_level():
    rumour = ev("Series B of EUR 40M (search summary)", field="funding", tag="snippet", state="assumption")
    assert levels(registered(), rumour)["irl"].level == 3


def test_impact_area_without_a_claim_stays_unknown():
    oirl = levels(ev("Rotor Sail auxiliary wind propulsion for ships."))["oirl"]
    assert oirl.level is None
    assert oirl.areas == ["Towards 1.5°C"]


def test_impact_levels_and_the_self_reported_cap():
    assert levels(ev("Removes phosphorus from wastewater."))["oirl"].level == 1
    assert levels(ev("Removes up to 90% of phosphorus from wastewater."))["oirl"].level == 2
    own = ev(
        "Self-reported 400% biodiversity increase in a reef pilot, verified by a third-party lab",
        field="impact",
        family="site:reef.example",
    )
    oirl = levels(own)["oirl"]
    assert oirl.level == 3  # self-reported figures cap at 3
    assert "Thriving and Restored Marine Habitats" in oirl.areas
    assert oirl.thesis_quote


def test_confidence_reflects_independence():
    own_site = ev("38 Rotor Sails installed on 21 vessels", family="site:norsepower.com")
    assert levels(own_site)["trl"].confidence == "low"
    assert levels(registered())["irl"].confidence == "medium"
    a = ev("Public contract award: boats (buyer: A)", field="public_contracts", tag="ted", family="ted")
    b = ev("Customer logos on site: Port of Turku", family="research_pack")
    assert levels(a, b)["brl"].confidence in ("medium", "high")
