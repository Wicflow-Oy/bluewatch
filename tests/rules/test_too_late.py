"""The too-late gates: an established company is "Not for us" with the deciding rule and its source, never a
lead. Each gate reads a stated value only, so an unknown never closes it."""

from datetime import date

import pytest

from bluewatch.bridges.rank import for_company
from bluewatch.models import Registry
from bluewatch.rules.assess import assess
from bluewatch.rules.fit import too_late
from bluewatch.rules.funding import funding_opportunities
from bluewatch.rules.investors import match
from bluewatch.rules.nextsteps import order
from bluewatch.rules.presets import StageWindow, load_preset
from bluewatch.rules.readiness import assess_levels
from bluewatch.rules.score import score
from bluewatch.rules.seed_adapter import demo_items
from tests.rules.helpers import company, ev

TODAY = date(2026, 10, 17)
BLUE = load_preset("blue")
CONTROLS = {"NO:964118191": "Mowi", "FI:0128631-1": "Wärtsilä", "NO:979750730": "Kongsberg Maritime"}


def _with(c, **registry):
    return c.model_copy(update={"registry": c.registry.model_copy(update=registry)})


def _gate(c, evidence=(), preset=BLUE):
    return too_late(c, list(evidence), preset, TODAY)


def test_public_limited_company_form():
    listed = _with(company("NO:964118191"), form="ASA", founded=None)
    assert _gate(listed) == "public limited company (ASA, Brreg)"
    assert _gate(_with(company(), form="OYJ")) == "public limited company (OYJ, PRH)"
    assert _gate(company()) is None  # a private limited company (OY) founded last month


def test_age_past_the_preset_window_names_the_date_and_its_source():
    assert _gate(company(founded=date(2012, 10, 22))) == "registered 2012 (PRH), over 10 years ago"
    from_site = ev("Founded 2007", field="founded", family="site:minesto.com", value="2007")
    assert _gate(company(founded=None), [from_site]) == "founded 2007 (company site), over 10 years ago"


def test_a_preset_without_its_own_age_limit_uses_fifteen_years():
    no_limit = BLUE.model_copy(update={"stage_window": StageWindow(irl_min=2, irl_max=8)})
    assert _gate(company(founded=date(2012, 10, 22)), preset=no_limit) is None
    assert _gate(company(founded=date(2010, 1, 4)), preset=no_limit) == "registered 2010 (PRH), over 15 years ago"


def test_more_than_250_employees_where_the_register_states_it():
    big = _with(company("NO:979750730", founded=date(2024, 1, 2)), employees=3681)
    assert _gate(big) == "3,681 employees (Brreg), over 250"
    assert _gate(_with(big, employees=250)) is None


def test_revenue_above_ten_million_only_from_a_filed_figure():
    filed = ev("Revenue EUR 25,000,000 (filed accounts)", field="revenue", tag="registry", value="25000000")
    assert _gate(company(), [filed]) == "revenue EUR 25,000,000 (PRH), over EUR 10,000,000"
    claimed = ev("Revenue EUR 25,000,000", field="revenue", tag="read", value="25000000")
    assert _gate(company(), [claimed]) is None  # a figure no register filed never closes the gate


def test_unknown_values_never_close_a_gate():
    unknown = company("SE:candela-ab", founded=None).model_copy(update={"registry": Registry(country="SE", id="")})
    assert _gate(unknown, [ev("Hydrofoiling electric boats")]) is None


def test_an_unknown_founding_date_earns_no_stage_credit():
    c = company(founded=None)
    evidence = [ev("Seed round of EUR 2M closed", field="funding"), ev("Electric boats for ports")]
    s = score(c, evidence, assess_levels(c, evidence, today=TODAY), today=TODAY)
    assert "stage_fit" not in s.potential_parts
    assert any("stage fit" in line for line in s.explanation if line.startswith("Unknown"))


def test_too_late_is_not_for_us_with_the_rule_and_no_investment_readiness():
    listed = _with(company("NO:964118191", one_liner="Salmon farming at scale"), form="ASA", founded=None)
    a = assess(listed, [ev("Salmon farming at scale")])
    assert a.score.group == "not_for_us" and "too_late" in a.flags
    assert "Not for us: too late: public limited company (ASA, Brreg)" in a.score.explanation
    assert a.score.potential == 0.0 and a.score.potential_parts["thesis_fit"] > 0.5  # never reads as High
    irl = next(lv for lv in a.levels if lv.key == "irl")
    assert not irl.applicable and irl.level is None
    assert irl.unknown_reason.startswith("An established company, outside a pre-seed to Series A window")


def test_too_late_is_the_deciding_reason_before_off_thesis():
    old_off = company(vertical="other", one_liner="Sauna-inspired natural skincare", founded=date(1990, 5, 1))
    a = assess(old_off, [ev("Sauna-inspired natural skincare")])
    assert a.score.explanation[-1] == "Not for us: too late: registered 1990 (PRH), over 10 years ago"


@pytest.fixture(scope="module")
def controls():
    items = {c.id: (c, e) for c, e, _ in demo_items()}
    return {cid: items[cid] for cid in CONTROLS}


@pytest.mark.parametrize("preset", ["blue", "climate_circular"])
def test_the_famous_controls_read_too_late_with_their_rule(controls, preset):
    rules = {}
    for cid, (c, e) in controls.items():
        a = assess(c, e, preset=preset)
        assert a.score.group == "not_for_us" and "too_late" in a.flags, CONTROLS[cid]
        rules[cid] = a.score.explanation[-1]
    assert rules == {
        "NO:964118191": "Not for us: too late: public limited company (ASA, Brreg)",
        "FI:0128631-1": "Not for us: too late: public limited company (OYJ, PRH)",
        "NO:979750730": "Not for us: too late: registered 1998 (Brreg), over 10 years ago",
    }


@pytest.mark.parametrize("mode", ["apelago", "redstone"])
def test_a_too_late_company_gets_no_next_step_and_no_investor_lead(controls, mode):
    c, e = controls["NO:964118191"]
    a = assess(c, e)
    investors = match(c, a, mode=mode, limit=60, today=TODAY)
    assert investors and all(m.when == "not_a_fit" for m in investors)
    rule = "Past the stage window: public limited company (ASA, Brreg)"
    assert all(m.fit_label.endswith(rule) for m in investors)  # Redstone's own fund leads with its name
    opportunities = funding_opportunities(c, a, mode=mode, today=TODAY)
    bridges = for_company(c.id, today=TODAY, limit=3, mode=mode)
    assert order(c, a, opportunities, investors, bridges, today=TODAY) == []


@pytest.mark.parametrize("cid", list(CONTROLS))
def test_funding_for_a_too_late_company_is_not_applicable_with_the_rule(controls, cid):
    c, e = controls[cid]
    a = assess(c, e)
    opportunities = funding_opportunities(c, a, mode="apelago", today=TODAY)
    assert opportunities and all(o.tier == "excluded" for o in opportunities)  # never listed as possible
    assert {o.rule for o in opportunities} == {
        a.score.explanation[-1].replace("Not for us: too late", "Past the stage window")
    }
    assert all(o.action.startswith("Not applicable") and o.upgrade_path is None for o in opportunities)


def test_a_company_past_series_a_reads_past_the_window_too():
    late_stage = company(founded=date(2024, 1, 2))
    a = assess(late_stage, [ev("Series B round of EUR 40M closed", field="funding"), ev("Electric boats for ports")])
    assert "too_late" in a.flags
    assert {m.fit_label for m in match(late_stage, a, mode="apelago", today=TODAY)} == {
        "Past the stage window: Series A or later, listed or acquired"
    }
