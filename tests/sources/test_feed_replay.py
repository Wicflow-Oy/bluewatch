import json
import re
from datetime import date

from bluewatch.models import ConnectorResult, Registry
from bluewatch.sources import common, feed, prh, replay
from bluewatch.sources.common import FIXTURES, LIVE_FIXTURES


def test_feed_combines_three_registers():
    records, signals, statuses = feed.new_companies(date(2026, 10, 13), date(2026, 10, 16))
    assert {r.country for r in records} == {"FI", "NO", "EE"}
    assert [s.source for s in statuses] == ["prh", "brreg", "rik"]
    assert all(s.state == "cached" for s in statuses)
    assert len(signals) == len(records)


def test_feed_removes_natural_persons(monkeypatch):
    person = common.private_person(Registry(country="FI", id="1234567-8", name="Testi Henkilö"))
    company = Registry(country="FI", id="7654321-0", name="Meri Oy", form="OY")

    def fake(since, until):
        signals = [prh.newly_founded(r, common.now()) for r in (company, person.model_copy(update={"name": "x"}))]
        return ConnectorResult(
            records=[person, company], signals=signals, status=common.source_status("prh", "live", records=2)
        )

    monkeypatch.setattr(prh, "fetch_new_companies", fake)
    records, signals, _ = feed.new_companies(date(2026, 10, 13), date(2026, 10, 13))
    assert "1234567-8" not in {r.id for r in records} | {s.entity_ref.id for s in signals}
    assert "7654321-0" in {r.id for r in records}


def test_feed_reports_a_crashed_connector(monkeypatch):
    def broken(since, until):
        raise KeyError("companies")

    monkeypatch.setattr(prh, "fetch_new_companies", broken)
    _, _, statuses = feed.new_companies(date(2026, 10, 13), date(2026, 10, 13))
    assert statuses[0].state == "unavailable" and statuses[0].source == "prh"


def test_replay_uses_real_dates_inside_the_window():
    signals = replay.replay(date(2026, 10, 1), date(2026, 10, 16))
    kinds = {(s.source, s.type) for s in signals}
    assert {
        ("prh", "newly_founded"),
        ("brreg", "newly_founded"),
        ("rik", "newly_founded"),
        ("prh", "share_issue"),
        ("ted", "open_tender"),
    } <= kinds
    dated = [s for s in signals if s.event_date]
    assert all(date(2026, 10, 1) <= s.event_date <= date(2026, 10, 16) for s in dated)
    assert dated == sorted(dated, key=lambda s: (s.event_date, s.id))
    assert len({s.id for s in signals}) == len(signals)


def test_recorded_fixtures_hold_no_contact_details():
    email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    for path in sorted(LIVE_FIXTURES.iterdir()):
        text = path.read_text(encoding="utf-8")
        assert not email.search(text), path.name
        assert not {"epostadresse", "telefon", "mobil"} & set(re.findall(r'"(\w+)":', text)), path.name
    updates = json.loads((FIXTURES / "live_2026-10-17/brreg_updates_2026-10-16.json").read_text(encoding="utf-8"))
    assert all("value" not in change for item in updates["items"] for change in item["endringer"])
