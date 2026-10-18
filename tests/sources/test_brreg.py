import logging
from datetime import date, datetime, timezone

import httpx

from bluewatch import seed
from bluewatch.sources import brreg

DAY = date(2026, 10, 16)
SINCE = datetime(2026, 10, 16, 6, tzinfo=timezone.utc)


def recorded_day() -> dict:
    return seed.fixture(f"sources/{brreg.LIVE_DAY}")


def enk() -> dict:
    """A synthetic sole trader: the recorded fixtures never contain one."""
    return {
        "organisasjonsnummer": "999999999",
        "navn": "Ola Testperson",
        "organisasjonsform": {"kode": "ENK"},
        "forretningsadresse": {"kommune": "OSLO"},
        "registreringsdatoEnhetsregisteret": "2026-10-16",
    }


def test_parse_entity():
    raw = recorded_day()["enheter"][0]
    record = brreg.parse_entity(raw)
    assert record.country == "NO" and record.id == raw["organisasjonsnummer"]
    assert record.form == "AS" and record.status == "registered"
    assert record.municipality == raw["forretningsadresse"]["kommune"].title()


def test_enk_is_a_private_natural_person():
    record = brreg.parse_entity(enk())
    assert record.natural_person and record.name is None and record.municipality is None


def test_offline_new_companies_for_the_recorded_day():
    result = brreg.fetch_new_companies(DAY, DAY, offline=True)
    assert result.status.state == "cached"
    assert len(result.records) == recorded_day()["totalElements"] == 127
    assert all(s.event_date == DAY for s in result.signals)
    missing = [r for r in result.records if r.industry_code is None]
    assert missing, "new entities without a NACE code keep industry_code=None"


def test_offline_candidate_weeks_keep_the_registration_week():
    result = brreg.fetch_new_companies(date(2026, 9, 14), date(2026, 9, 20), offline=True)
    assert len(result.records) == 28
    signal = result.signals[0]
    assert signal.event_date is None
    assert signal.payload["registered_between"] == ["2026-09-14", "2026-09-20"]
    assert "not fully recorded" in result.status.detail


def test_live_new_companies_skip_people_in_signals(fake_net):
    page = {"_embedded": {"enheter": recorded_day()["enheter"][:3] + [enk()]}, "page": {"totalElements": 4}}
    fake_net.routes["/enheter"] = page
    result = brreg.fetch_new_companies(DAY, DAY, offline=False)
    assert result.status.state == "live"
    assert sum(r.natural_person for r in result.records) == 1
    assert len(result.signals) == 3 and "999999999" not in {s.entity_ref.id for s in result.signals}
    assert fake_net.calls[0].params["organisasjonsform"] == "AS"


def test_live_http_error_falls_back(fake_net):
    fake_net.routes["/enheter"] = (503, {"error": "down"})
    result = brreg.fetch_new_companies(DAY, DAY, offline=False)
    assert result.status.state == "cached"
    assert "HTTP 503" in result.status.detail


def test_lookup_live_recorded_and_missing(fake_net):
    fake_net.routes["/enheter/938525420"] = seed.fixture(f"sources/{brreg.LIVE_LOOKUP}")["response"]
    fake_net.routes["/enheter/999999999"] = enk()
    fake_net.routes["/enheter/111111111"] = (404, {})
    assert brreg.lookup("938525420", offline=False).name == "HAVNIO AS"
    assert brreg.lookup("999 999 999", offline=False).natural_person
    missing = brreg.lookup_result("111111111", offline=False)
    assert missing.status.state == "live" and missing.records == []
    assert brreg.lookup_result("938525420", offline=True).status.state == "cached"
    assert brreg.lookup_result("12", offline=False).status.state == "unavailable"


def test_change_stream_counts_and_watched_changes():
    items = seed.fixture(f"sources/{brreg.LIVE_UPDATES}")["items"]
    watched = next(i["organisasjonsnummer"] for i in items if "organisasjonsnummer" in i)
    result = brreg.fetch_updates(SINCE, watch=[watched], offline=True)
    assert result.status.state == "cached"
    assert f"{len(items)} updates" in result.status.detail
    assert [r.id for r in result.records] == [watched]
    assert result.signals == []


def test_change_stream_live_looks_up_watched_changes(fake_net):
    fake_net.routes["oppdateringer"] = {
        "_embedded": {
            "oppdaterteEnheter": [
                {
                    "oppdateringsid": 1,
                    "dato": "2026-10-16T06:01:00.000Z",
                    "organisasjonsnummer": "938525420",
                    "endringstype": "Endring",
                    "endringer": [
                        {"op": "add", "path": "/hjemmeside", "value": "havnio.no"},
                        {"op": "add", "path": "/epostadresse", "value": "x@y.no"},
                    ],
                },
                {
                    "oppdateringsid": 2,
                    "dato": "2026-10-16T06:02:00.000Z",
                    "organisasjonsnummer": "123456789",
                    "endringstype": "Ny",
                },
            ]
        },
        "page": {"totalElements": 2},
    }
    fake_net.routes["/enheter/938525420"] = seed.fixture(f"sources/{brreg.LIVE_LOOKUP}")["response"]
    result = brreg.fetch_updates(SINCE, watch={"938525420"}, offline=False)
    assert result.status.state == "live"
    assert "1 new, 1 changed (1 set a website)" in result.status.detail
    assert result.status.detail.endswith("; 1 watched organisation changed")
    assert [r.name for r in result.records] == ["HAVNIO AS"]
    assert fake_net.calls[0].params["includeChanges"] == "true"


def test_changed_fields_never_reads_contacts():
    item = {"endringer": [{"path": "/epostadresse"}, {"path": "/mobil"}, {"path": "/naeringskode1/kode"}]}
    assert brreg.changed_fields(item) == ["naeringskode1"]


def test_a_failed_live_lookup_is_logged_without_the_id(fake_net, caplog):
    fake_net.routes["/enheter/938525420"] = httpx.ReadTimeout("slow")
    caplog.set_level(logging.WARNING)
    result = brreg.lookup_result("938525420", offline=False)
    assert result.status.detail == "lookup timed out; not counted as zero"
    assert [r.getMessage() for r in caplog.records] == ["brreg lookup failed: timed out"]
