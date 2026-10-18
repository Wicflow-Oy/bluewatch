import threading
from datetime import date, datetime

from bluewatch import demo
from bluewatch.config import HELSINKI


def test_list_rows_lead_with_the_cards_first_step():
    short = demo.shortlist("apelago")
    assert 0 < len(short.entries) <= 10
    for entry in short.entries:
        first = demo.venture_card(entry.company_id, "apelago").next_steps
        if first:
            assert entry.next_action == first[0].action
            assert entry.deadline == first[0].deadline


def test_alpo_row_points_at_the_sansia_tender():
    short = demo.shortlist("apelago")
    alpo = next(e for e in short.entries if e.name == "Alpo Pro Boats")
    assert "Sansia" in alpo.next_action and alpo.deadline.isoformat() == "2026-10-30"


def test_precomputed_results_are_cached_per_day(monkeypatch):
    calls = []

    @demo.per_day
    def computed(company_id: str, preset: str = "blue") -> int:
        calls.append(company_id)
        return len(calls)

    assert computed("a") == computed("a", "blue") == computed(company_id="a") == 1
    monkeypatch.setenv("BLUEWATCH_TODAY", "2026-10-18")
    assert computed("a") == 2  # a new day recomputes deadlines and countdowns


def test_the_last_digest_is_the_latest_monday_at_seven_in_helsinki():
    assert demo.last_digest(date(2026, 10, 17)) == datetime(2026, 10, 12, 7, tzinfo=HELSINKI)
    assert demo.last_digest(date(2026, 10, 12)) == datetime(2026, 10, 12, 7, tzinfo=HELSINKI)
    assert demo.last_digest(date(2026, 10, 11)) == datetime(2026, 10, 5, 7, tzinfo=HELSINKI)


def test_the_caches_are_warmed_again_when_the_date_changes(monkeypatch):
    warmed: list[str] = []
    checks = iter(["2026-10-17", "2026-10-18", None])  # the date at each later check; None stops the loop
    stop = threading.Event()

    def next_check(_seconds: float) -> bool:
        day = next(checks)
        if day is not None:
            monkeypatch.setenv("BLUEWATCH_TODAY", day)
        return day is None

    monkeypatch.setattr(demo, "warm", lambda: warmed.append(demo.settings().today.isoformat()))
    monkeypatch.setattr(stop, "wait", next_check)
    demo.keep_warm(stop)
    assert warmed == ["2026-10-17", "2026-10-18"]
