from datetime import date

from bluewatch.bridges.rank import all_bridges, for_company, urgency

ALPO = "FI:3101791-3"


def test_alpo_gets_b1_first_then_b2(today):
    bridges = for_company(ALPO, today=today)
    assert [b.id for b in bridges[:2]] == ["B1", "B2"]
    assert len(bridges) <= 3


def test_rank_parts_reproduce_the_order(today):
    bridges = for_company(ALPO, today=today)
    for bridge in bridges:
        parts = bridge.rank_parts
        assert parts["score"] == round(parts["deadline"] * parts["fit"] * parts["evidence"], 3)
    scores = [b.rank_parts["score"] for b in bridges]
    assert scores == sorted(scores, reverse=True)
    assert bridges[0].rank_parts["days_left"] == 13


def test_urgency_steps():
    assert urgency(None, date(2026, 10, 17)) == 0.4
    assert urgency(date(2026, 10, 30), date(2026, 10, 17)) == 1.0
    assert urgency(date(2027, 1, 30), date(2026, 10, 17)) == 0.8
    assert urgency(date(2027, 6, 30), date(2026, 10, 17)) == 0.6
    assert urgency(date(2030, 1, 1), date(2026, 10, 17)) == 0.5
    assert urgency(date(2026, 10, 1), date(2026, 10, 17)) == 0.0


def test_generated_copies_of_seed_bridges_are_dropped(today):
    ids = [b.id for b in all_bridges(today)]
    assert "won_before_open_again/FI:3101791-3/sansia" not in ids  # B1 already says it
    assert len(ids) == len(set(ids))


def test_expired_deadlines_are_dropped():
    ids = [b.id for b in for_company(ALPO, today=date(2026, 11, 7))]
    assert "B1" not in ids and "B2" in ids


def test_never_padded_and_mode_filtered(today):
    assert [b.id for b in for_company("name:sensemakers", today=today)] == ["B7"]
    assert for_company("FI:0000000-0", today=today) == []
    redstone = for_company("FI:3652359-1", today=today, mode="redstone")
    assert all(b.mode in ("redstone", "both") for b in redstone)
