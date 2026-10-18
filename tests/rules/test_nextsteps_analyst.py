"""The judge's check: the top five next steps for five demo companies, as an A'Pelago analyst would
read them. Runs the same chain as the venture card (opportunities, investors, bridges, order)."""

from datetime import date

import pytest

from bluewatch.bridges.rank import for_company
from bluewatch.rules.assess import assess
from bluewatch.rules.funding import funding_opportunities
from bluewatch.rules.investors import match
from bluewatch.rules.nextsteps import order
from bluewatch.rules.seed_adapter import demo_items

TODAY = date(2026, 10, 17)
STAGE_GATED = ("EIC Accelerator", "EIC Pathfinder")


@pytest.fixture(scope="module")
def steps():
    items = {c.id: (c, e) for c, e, _ in demo_items()}

    def top5(company_id: str, mode: str = "apelago"):
        c, e = items[company_id]
        a = assess(c, e)
        opportunities = funding_opportunities(c, a, mode=mode, today=TODAY)
        bridges = for_company(company_id, today=TODAY, limit=3, mode=mode)
        return order(c, a, opportunities, match(c, a, mode=mode), bridges, today=TODAY)[:5]

    return top5


def _titles(top):
    return " | ".join(s.title for s in top)


def test_havnio_pre_seed_gets_programmes_before_any_stage_gated_grant(steps):
    top = steps("NO:938525420")
    assert top[0].kind in ("confirm_match", "ask_company", "programme")
    assert not any(t in _titles(top) for t in STAGE_GATED)
    assert "Slovenian" not in _titles(top) and "Business Finland" not in _titles(top)  # other regions' calls
    kinds = [s.kind for s in top]
    assert kinds.index("programme") < min((i for i, k in enumerate(kinds) if k in ("grant", "investor")), default=99)


def test_meriva_consultancy_gets_programme_roles_and_no_investors(steps):
    top = steps("FI:3652359-1")
    assert top[0].kind == "ask_company"  # thin evidence: the gaps are the next step
    assert all(s.kind != "investor" for s in top)
    assert "Northern Blue" in _titles(top)
    assert not any(t in _titles(top) for t in STAGE_GATED)


def test_alpo_starts_with_the_tender_it_has_won_before(steps):
    top = steps("FI:3101791-3")
    assert top[0].title == "Sansia Oy" and top[0].deadline == date(2026, 10, 30)
    assert "June award" in top[0].action


@pytest.mark.parametrize("company_id", ["FI:3134791-2", "NO:928178056"])  # Marine Charging Point, Oceanbox
def test_no_out_of_region_or_apply_by_tomorrow_calls(steps, company_id):
    top = steps(company_id)
    assert "Slovenian" not in _titles(top)
    for s in top:
        assert s.deadline is None or s.deadline >= TODAY
        if s.title.startswith("EIC Accelerator"):
            assert s.deadline is None and "short proposal" in s.action  # full proposals need an invitation


def test_steps_never_repeat_a_call(steps):
    for company_id in ("NO:938525420", "FI:3652359-1", "FI:3101791-3", "FI:3134791-2", "NO:928178056"):
        keys = [s.title.split(" (")[0].lower() for s in steps(company_id)]
        assert len(keys) == len(set(keys))


def test_a_cohort_company_is_not_pointed_back_to_its_own_programmes(steps):
    for cid in ("FI:3197621-7", "FI:3392875-3"):  # Sub Marine Store and NPHarvest, both in an A'Pelago batch
        top = steps(cid)
        assert top and "A'Pelago" not in _titles(top)


def test_a_portfolio_company_gets_no_step_towards_its_own_investor(steps):
    for mode in ("apelago", "redstone"):
        assert "Redstone Blue" not in _titles(steps("FI:2902007-2", mode))  # Kelluu


def test_thin_evidence_reads_in_words_not_a_score(steps):
    ask = next(s for s in steps("NO:938525420") if s.kind == "ask_company")
    assert ask.why.startswith("The evidence is thin; unknown: ")
