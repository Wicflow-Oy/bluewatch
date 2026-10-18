from datetime import date

import pytest

from bluewatch.rules.assess import assess
from bluewatch.rules.investors import load_investors, match
from bluewatch.rules.presets import load_preset
from bluewatch.rules.seed_adapter import demo_items

TODAY = date(2026, 10, 17)


@pytest.fixture(scope="module")
def cards():
    return {c.id: (c, assess(c, e)) for c, e, _ in demo_items()}


def test_all_sixty_investors_load_with_unique_ids():
    investors = load_investors()
    assert len(investors) == 60 == len({i.id for i in investors})
    assert {"redstone-blue", "fiban", "katapult-ocean"} <= {i.id for i in investors}
    assert sum(i.exclude_from_matching for i in investors) == 2


def test_excluded_investors_are_never_matched(cards):
    excluded = {i.id for i in load_investors() if i.exclude_from_matching}
    for c, a in cards.values():
        assert not excluded & {m.investor_id for m in match(c, a, mode="redstone", limit=60, today=TODAY)}


def test_prioritised_order_reproducible_from_parts(cards):
    c, a = cards["NO:938525420"]  # HAVNIO
    weights = load_preset("blue").weights.investor
    matches = match(c, a, mode="apelago", limit=60, today=TODAY)
    order = {"now": 0, "later": 1, "not_a_fit": 2}
    keys = [(order[m.when], -m.score, m.investor_id) for m in matches]
    assert keys == sorted(keys)
    assert [m.rank for m in matches] == list(range(1, len(matches) + 1))
    for m in matches:
        assert abs(sum(weights[k] * v for k, v in m.parts.items()) - m.score) < 1e-2
        assert m.why and m.fit_label


def test_geography_tiers_and_mismatch(cards):
    c, a = cards["FI:3101791-3"]  # a Finnish boat builder
    by_id = {m.investor_id: m for m in match(c, a, mode="apelago", limit=60, today=TODAY)}
    assert by_id["indico-capital-partners"].when == "not_a_fit"  # Portugal-only ocean fund
    assert by_id["business-finland"].parts["geography"] == 1.0  # national
    assert by_id["redstone-blue"].parts["geography"] > by_id["planet-a-ventures"].parts["geography"]  # Nordic > EU


def test_verification_order_and_angel_networks(cards):
    c, a = cards["FI:3101791-3"]
    by_id = {m.investor_id: m for m in match(c, a, mode="apelago", limit=60, today=TODAY)}
    assert by_id["katapult-ocean"].parts["verification"] > by_id["aqua-spark"].parts["verification"]
    assert any("angel network" in line.lower() for line in by_id["fiban"].why)


def test_redstone_mode_flags_redstone_blue(cards):
    c, a = cards["FI:3101791-3"]
    redstone = {m.investor_id: m for m in match(c, a, mode="redstone", today=TODAY)}
    apelago = {m.investor_id: m for m in match(c, a, mode="apelago", limit=60, today=TODAY)}
    assert redstone["redstone-blue"].fit_label.startswith("Redstone Blue:")
    assert not apelago["redstone-blue"].fit_label.startswith("Redstone Blue:")


def test_too_late_and_service_companies(cards):
    late_c, late_a = cards["FI:2506251-5"]  # Norsepower, registered 2012
    late = {m.investor_id: m for m in match(late_c, late_a, mode="redstone", today=TODAY)}
    assert late["redstone-blue"].when == "not_a_fit"  # always shown in Redstone mode, even when not a fit
    service_c, service_a = cards["FI:3652359-1"]  # Meriva, a consultancy
    service = {m.investor_id: m for m in match(service_c, service_a, mode="redstone", today=TODAY)}
    assert service["redstone-blue"].when == "later"
    assert "service business" in service["redstone-blue"].fit_label


def test_no_investor_is_a_fit_while_what_the_company_does_is_unknown():
    from bluewatch.models import Company, Registry, Resolution

    art = Company(
        id="EE:17000257",
        names=["Liisu Art OÜ"],
        resolution=Resolution(state="resolved", reason="test"),
        registry=Registry(country="EE", id="17000257", name="Liisu Art OÜ", founded=date(2024, 6, 3)),
    )
    matches = match(art, assess(art, []), mode="apelago", limit=60, today=TODAY)
    assert matches and not [m for m in matches if m.when == "now"]
    icebreaker = next(m for m in matches if m.name == "Icebreaker.vc")
    assert icebreaker.fit_label == "Partial fit: what the company does is not known yet"


def test_an_investor_is_never_a_new_lead_for_a_company_it_already_holds(cards):
    for cid in ("FI:2902007-2", "FI:3274823-2"):  # Kelluu (tagged Redstone Blue portfolio), Valkama (on its list)
        c, a = cards[cid]
        for mode in ("apelago", "redstone"):
            fund = next(m for m in match(c, a, mode=mode, today=TODAY) if m.investor_id == "redstone-blue")
            assert fund.when == "not_a_fit"
            assert fund.fit_label.endswith("Already in its portfolio: an existing relationship, not a new lead")
    c, a = cards["SE:swedish-algae-factory-ab"]  # named in Almi Invest GreenTech's portfolio
    almi = {m.investor_id: m for m in match(c, a, mode="apelago", today=TODAY)}["almi-invest-greentech"]
    assert almi.when == "not_a_fit" and almi.fit_label.startswith("Already in its portfolio")
