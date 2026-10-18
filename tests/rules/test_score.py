from datetime import date

from bluewatch.rules.assess import assess
from bluewatch.rules.readiness import assess_levels
from bluewatch.rules.score import score
from bluewatch.rules.seed_adapter import demo_items
from tests.rules.helpers import company, ev, registered

TODAY = date(2026, 10, 17)


def _score(c, evidence, preset="blue"):
    return score(c, evidence, assess_levels(c, evidence, preset=preset), preset=preset, today=TODAY)


def test_unknowns_lower_only_the_evidence_axis():
    c = company(one_liner="Mobile payment for guest harbours and boat berths")
    base = [registered(), ev("Mobile payment for guest harbours and boat berths")]
    gaps = [
        ev("Team: unknown", field="team", state="unknown", tag="dossier", why_unknown="No team page"),
        ev("Pricing: unknown", field="business_model", state="unknown", tag="dossier"),
    ]
    before, after = _score(c, base), _score(c, base + gaps)
    assert after.potential == before.potential
    assert after.evidence <= before.evidence


def test_unknown_parts_are_left_out_not_counted_as_zero():
    c = company(founded=None)
    s = _score(c, [ev("Harbour software")])
    assert "stage_fit" not in s.potential_parts  # no register record, no age: stage unknown
    assert any("left out of potential" in line for line in s.explanation)


def test_known_negatives_do_lower_potential():
    young, old = company(), company(founded=date(2012, 10, 22))
    evidence = [ev("Rotor sail wind propulsion for ships")]
    assert _score(old, evidence).group == "not_for_us"  # older than 10 years: past the window
    assert _score(old, evidence).potential < _score(young, evidence).potential


def test_off_thesis_is_not_for_us_and_pre_launch_is_not_yet():
    off = company(vertical="other", one_liner="Sauna-inspired natural skincare")
    assert _score(off, [ev("Sauna-inspired natural skincare")]).group == "not_for_us"
    watch = company(tags=["pre_launch"])
    assert _score(watch, [registered(), ev("Water-safety service; waitlist page")]).group == "not_yet"


def test_demo_companies_land_in_the_documented_groups():
    items = {c.id: (c, e) for c, e, _ in demo_items()}
    meriva = assess(*items["FI:3652359-1"])
    assert meriva.score.group == "dive_deeper"  # promising, thin evidence: missing info is not a low score
    assert assess(*items["FI:3101791-3"]).score.group == "act_now"  # Alpo: public buyers, solid evidence
    assert assess(*items["FI:2506251-5"]).score.group == "not_for_us"  # Norsepower: too late


def test_assessment_is_versioned_and_deterministic():
    c, e, _ = demo_items()[0]
    first, second = assess(c, e), assess(c, e)
    assert first == second
    assert first.rules_version.startswith("rules-")
