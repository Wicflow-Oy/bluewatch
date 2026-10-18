from datetime import date

import httpx

from bluewatch import seed
from bluewatch.sources import ted

TODAY = date(2026, 10, 17)


def test_open_tenders_offline_carry_deadline_cpv_and_buyer():
    result = ted.open_tenders(["34521000"], ["FI"], today=TODAY, offline=True)
    assert result.status.state == "cached"
    by_pub = {s.payload["publication_number"]: s for s in result.signals}
    assert set(by_pub) == {"668013-2026", "713640-2026"}
    sansia = by_pub["668013-2026"]
    assert (sansia.type, sansia.payload["buyer"], sansia.payload["deadline"]) == (
        "open_tender",
        "Sansia Oy",
        "2026-10-30",
    )
    assert "34521000" in sansia.payload["cpv"] and sansia.payload["buyer_country"] == ["FI"]
    assert by_pub["713640-2026"].payload["deadline"] == "2026-11-06"
    assert sansia.url.endswith("/668013-2026")


def test_closed_tenders_are_left_out():
    later = ted.open_tenders(["34521000"], ["FI"], today=date(2026, 11, 1), offline=True)
    assert [s.payload["publication_number"] for s in later.signals] == ["713640-2026"]


def test_codes_never_recorded_are_not_reported_as_none():
    result = ted.open_tenders(["03"], ["FI"], today=TODAY, offline=True)
    assert result.signals == [] and "not counted as zero" in result.status.detail


def test_cpv_prefix_matches_sub_codes():
    notice = {"deadlines": ["2026-11-01"], "cpv": ["90733100"], "countries": ["FI"]}
    assert ted._keep(notice, ["90733000"], ["FI"], TODAY)
    assert not ted._keep(notice, ["34500000"], ["FI"], TODAY)


def test_open_tender_query():
    query = ted.open_tender_query(["345", "34521000"], ["FI", "SE"], date(2026, 6, 19))
    assert "buyer-country IN (FIN SWE)" in query
    assert "classification-cpv IN (34500000 34521000)" in query
    assert query.endswith("publication-date>=20260619")


def test_open_tenders_live(fake_net):
    fake_net.routes["notices/search"] = {"notices": seed.fixture(f"sources/{ted.LIVE_OPEN}")["notices"]}
    result = ted.open_tenders(["34521000"], ["FI"], today=TODAY, offline=False)
    assert result.status.state == "live"
    assert {s.payload["publication_number"] for s in result.signals} == {"668013-2026", "713640-2026"}
    assert fake_net.calls[0].body["scope"] == "ACTIVE"


def test_open_tenders_live_failure_falls_back(fake_net):
    fake_net.routes["notices/search"] = httpx.ConnectError("down")
    result = ted.open_tenders(["34521000"], ["FI"], today=TODAY, offline=False)
    assert result.status.state == "cached"
    assert result.status.detail.startswith("live call could not reach the service")


def test_awards_by_winner_rebuild_the_alpo_pro_boats_bridge():
    awards = {s.payload["publication_number"]: s for s in ted.awards_by_winner("3101791-3", "FI", offline=True)}
    assert {"423989-2026", "152432-2026", "433538-2025"} <= set(awards)
    june = awards["423989-2026"]
    assert june.type == "award" and june.payload["winner_id"] == "3101791-3"
    assert june.entity_ref.registry == "prh" and june.entity_ref.id == "3101791-3"
    assert june.event_date == date(2026, 6, 19)
    assert "C-luokka" in june.title and june.payload["buyer"] == "Varsinais-Suomen hyvinvointialue"
    assert june.payload["cpv"] == ["34513650"]


def test_awards_live_query_uses_every_id_shape(fake_net):
    fake_net.routes["notices/search"] = {"notices": seed.fixture(f"sources/{ted.LIVE_AWARDS}")["notices"]}
    result = ted.awards_result("FI31017913", "FI", offline=False)
    assert result.status.state == "live" and len(result.signals) == 3
    assert fake_net.calls[0].body["query"] == "winner-identifier IN (3101791-3 31017913 FI31017913)"


def test_unrecorded_winner_is_unavailable():
    assert ted.awards_result("1234567-8", "FI", offline=True).status.state == "unavailable"


def test_id_variants():
    assert ted.id_variants("994353098", "NO") == ["994353098", "NO994353098MVA"]
    assert ted.id_variants("16337664", "EE") == ["16337664"]
