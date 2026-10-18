from datetime import date

import httpx

from bluewatch import seed
from bluewatch.sources import prh

DAY = date(2026, 10, 13)


def recorded_day() -> dict:
    return seed.fixture(f"sources/{prh.LIVE_DAY}")


def test_parse_company_from_a_recorded_response():
    record = prh.lookup("3101791-3", offline=True)
    assert record.name == "Alpo Pro Boats Oy"  # the current name, not the 2019 one
    assert record.form == "OY"
    assert record.municipality == "Rauma"  # from the municipality code, not the postal city
    assert record.website == "www.alpovene.fi"
    assert record.founded == date(2019, 11, 26)


def test_missing_industry_code_stays_none():
    raw = dict(recorded_day()["companies"][0])
    raw.pop("mainBusinessLine", None)
    record = prh.parse_company(raw)
    assert record.industry_code is None and record.industry_scheme is None


def test_sole_trader_is_a_private_natural_person():
    raw = dict(recorded_day()["companies"][0])
    raw["companyForms"] = [
        {"type": "26", "descriptions": [{"languageCode": "1", "description": "Yksityinen elinkeinonharjoittaja"}]}
    ]
    record = prh.parse_company(raw)
    assert record.natural_person and record.name is None and record.municipality is None


def test_offline_new_companies_for_a_recorded_day():
    result = prh.fetch_new_companies(DAY, DAY, offline=True)
    assert result.status.state == "cached"
    assert len(result.records) == recorded_day()["totalResults"] == 88
    assert {s.type for s in result.signals} == {"newly_founded"}
    assert all(s.event_date == DAY for s in result.signals)
    assert "not fully recorded" not in result.status.detail


def test_offline_gap_is_unavailable_not_empty():
    result = prh.fetch_new_companies(date(2026, 3, 1), date(2026, 3, 7), offline=True)
    assert result.status.state == "unavailable"
    assert "not counted as zero" in result.status.detail
    assert result.records == []


def test_partly_recorded_window_says_so():
    result = prh.fetch_new_companies(date(2026, 10, 5), date(2026, 10, 16), offline=True)
    assert result.status.state == "cached"
    assert "not fully recorded" in result.status.detail


def test_live_new_companies_through_net(fake_net):
    fake_net.routes["opendata-ytj-api"] = recorded_day()
    result = prh.fetch_new_companies(DAY, DAY, offline=False)
    assert result.status.state == "live"
    assert len(result.records) == 88
    params = fake_net.calls[0].params
    assert params["businessIdRegistrationStart"] == "2026-10-13" and params["companyForm"] == "OY"


def test_live_failure_falls_back_to_recorded_data(fake_net):
    fake_net.routes["opendata-ytj-api"] = httpx.ConnectTimeout("slow")
    result = prh.fetch_new_companies(DAY, DAY, offline=False)
    assert result.status.state == "cached"
    assert result.status.detail.startswith("live call timed out")
    assert len(result.records) == 88


def test_lookup_live_and_recorded(fake_net):
    fake_net.routes["opendata-ytj-api"] = seed.fixture(f"sources/{prh.LIVE_LOOKUP}")["response"]
    live = prh.lookup_result("FI31017913", offline=False)
    assert live.status.state == "live" and live.records[0].id == "3101791-3"
    assert fake_net.calls[0].params == {"businessId": "3101791-3"}
    recorded = prh.lookup_result("3101791-3", offline=True)
    assert recorded.status.state == "cached" and "live lookups are off" in recorded.status.detail


def test_lookup_rejects_malformed_ids_before_any_request(fake_net):
    assert prh.lookup_result("../../etc", offline=False).status.state == "unavailable"
    assert fake_net.calls == []


def test_lookup_not_found_live_is_not_unavailable(fake_net):
    fake_net.routes["opendata-ytj-api"] = {"totalResults": 0, "companies": []}
    result = prh.lookup_result("1234567-8", offline=False)
    assert result.status.state == "live" and result.records == []


def test_share_issues_one_signal_per_filing_date():
    signals = prh.share_issues("0209238-3", offline=True)
    assert [(s.type, s.event_date) for s in signals] == [("share_issue", date(2026, 10, 5))]
    assert {"ANTIP", "KOROI"} <= set(signals[0].payload["entry_codes"])


def test_share_issues_live(fake_net):
    fake_net.routes["registerednotices"] = {
        "companies": [
            {
                "publicNotices": [
                    {"registrationDate": "2026-05-02", "entryCodes": ["ANTIP", "OSLUKU"]},
                    {"registrationDate": "2026-05-02", "entryCodes": ["KOROI"]},
                    {"registrationDate": "2026-06-01", "entryCodes": ["TASE"]},
                ]
            }
        ]
    }
    result = prh.share_issues_result("3101791-3", offline=False)
    assert result.status.state == "live"
    assert [s.event_date for s in result.signals] == [date(2026, 5, 2)]


def test_share_issues_unrecorded_company_is_unavailable():
    assert prh.share_issues_result("1234567-8", offline=True).status.state == "unavailable"
