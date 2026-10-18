import json
from datetime import date

import httpx

from bluewatch.models import ConnectorResult
from bluewatch.sources import common, cordis, status


def test_cordis_projects_have_dates_and_participants():
    projects = {s.payload["acronym"]: s for s in cordis.load_projects()}
    assert len(projects) == 33
    algae = projects["AlgaePro BANOS"]
    assert algae.type == "eu_project" and algae.event_date == date(2023, 5, 21)
    assert algae.payload["start"] == "2023-04-01" and algae.payload["status"] == "running"
    origin = next(p for p in algae.payload["participants"] if p["name"] == "ORIGIN BY OCEAN OY")
    assert (origin["type"], origin["business_id"]) == ("PRC", "2982879-2")
    assert any(p["role"] == "thirdParty" for p in projects["GREEN RAY"].payload["participants"])
    assert algae.url == "https://cordis.europa.eu/project/id/101112943"


def test_cordis_from_another_export(tmp_path):
    path = tmp_path / "export.json"
    path.write_text(json.dumps({"projects": [{"grant_agreement_id": "1", "acronym": "X", "start": "2027-01-01"}]}))
    [project] = cordis.load_projects(path)
    assert project.payload["status"] == "not started"


def test_run_turns_an_exception_into_unavailable():
    def broken():
        raise httpx.ReadTimeout("slow")

    result = status.run("ted", broken)
    assert result.status.state == "unavailable"
    assert result.status.detail == "timed out; not counted as zero"


def test_strip_keeps_statuses_and_names_failures():
    ok = ConnectorResult(status=common.source_status("prh", "live", records=3))
    strip = status.strip([ok, ValueError("bad json")])
    assert [s.state for s in strip] == ["live", "unavailable"]
    assert strip[1].detail.startswith("unexpected response format")


def test_go_live_rules(monkeypatch):
    assert common.go_live(False) and not common.go_live(True)
    assert not common.go_live(None)  # tests run offline
    assert not common.go_live(None, lookup=True)
    monkeypatch.setenv("BLUEWATCH_LIVE_LOOKUPS", "1")
    assert common.go_live(None, lookup=True) and not common.go_live(None)


def test_parse_date_formats():
    expected = date(2026, 10, 16)
    for text in ("2026-10-16", "2026-10-16+02:00", "2026-10-16T06:00:00.000Z", "16.10.2026", "20261016"):
        assert common.parse_date(text) == expected
    assert common.parse_date("") is None and common.parse_date("soon") is None


def test_drop_contacts():
    raw = {"navn": "X AS", "epostadresse": "a@b.no", "nested": [{"telefon": "123", "kode": "AS"}]}
    assert common.drop_contacts(raw) == {"navn": "X AS", "nested": [{"kode": "AS"}]}


def test_recorded_detail_names_gaps():
    day = common.Recording("x.json", date(2026, 10, 13), date(2026, 10, 13), True, common.now(), "all registered")
    assert "not fully recorded" not in common.recorded_detail([day], date(2026, 10, 13), date(2026, 10, 13))
    assert "not fully recorded" in common.recorded_detail([day], date(2026, 10, 12), date(2026, 10, 13))
