import json

import httpx
import pytest

from bluewatch import lookup, net
from bluewatch.sources import brreg, prh, rik, search
from bluewatch.sources.common import name_rank
from bluewatch.sources.record import SEARCHES, search_fixture


def recorded(source: str) -> dict:
    return json.loads(search_fixture(source).read_text(encoding="utf-8"))["response"]


def live_registers(fake_net) -> None:
    fake_net.routes["opendata-ytj-api"] = recorded("prh")
    fake_net.routes["/enheter"] = recorded("brreg")
    fake_net.routes["ariregister.rik.ee"] = recorded("rik")


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("BLUEWATCH_LIVE_LOOKUPS", "1")


def test_name_rank_prefers_the_same_name_then_whole_words():
    assert name_rank("meriva", "Meriva Oy") == 0
    assert name_rank("HAVNIO", "HAVNIO AS") == 0
    assert name_rank("alpo", "Alpo Pro Boats Oy") == 1
    assert name_rank("alpo", "Alpokami OÜ") == 2
    assert name_rank("pro boats", "Alpo Pro Boats Oy") == 3
    assert name_rank("ovat", "Javatec Oy") is None
    assert name_rank("avatec", "Javatec Oy") == 4
    assert name_rank("havnio", "HAVINO AS") is None  # the register's loose match is dropped


def test_query_is_checked_before_any_register_is_asked():
    with pytest.raises(ValueError, match="at least 3"):
        search.search(" m  ")
    with pytest.raises(ValueError, match="at most 100"):
        search.search("x" * 101)


def test_offline_search_finds_recorded_and_precomputed_companies():
    result = search.search("meriva")
    assert [s.state for s in result.sources] == ["cached", "cached", "cached"]
    first = result.candidates[0]
    assert (first.name, first.business_id, first.company_id) == ("Meriva Oy", "3652359-1", "FI:3652359-1")
    assert len(result.candidates) <= search.MAX_CANDIDATES


def test_offline_search_reaches_a_precomputed_company_without_a_register_id():
    found = search.search("candela").candidates[0]
    assert found.company_id and found.business_id == ""


def test_country_limits_the_registers_and_the_precomputed_set():
    result = search.search("meriva", "EE")
    assert [s.source for s in result.sources] == ["rik"]
    assert {c.country for c in result.candidates} == {"EE"}


def test_live_search_reads_each_register_and_ranks_the_known_company_first(fake_net, live):
    live_registers(fake_net)
    for source, name in SEARCHES.items():
        result = search.search(name, {"prh": "FI", "brreg": "NO", "rik": "EE"}[source])
        assert result.sources[0].state == "live"
        assert result.candidates[0].company_id is not None, source
    assert all(call.params for call in fake_net.calls)


def test_live_search_drops_loose_matches(fake_net, live):
    live_registers(fake_net)
    names = [c.name for c in search.search("havnio", "NO").candidates]
    assert names == ["HAVNIO AS"]


def test_sole_traders_never_appear(fake_net, live):
    person = {"organisasjonsnummer": "999999999", "navn": "Havnio Testperson", "organisasjonsform": {"kode": "ENK"}}
    fake_net.routes["/enheter"] = {"_embedded": {"enheter": [person]}}
    result = search.search("havnio", "NO")
    assert [c.company_id for c in result.candidates] == ["NO:938525420"]  # the precomputed HAVNIO only
    assert "999999999" not in result.model_dump_json()


def test_a_failing_register_is_unavailable_and_the_others_still_answer(fake_net, live):
    live_registers(fake_net)
    fake_net.routes["opendata-ytj-api"] = httpx.ReadTimeout("slow")
    result = search.search("havnio")
    by_source = {s.source: s for s in result.sources}
    assert by_source["prh"].state == "unavailable" and "timed out" in by_source["prh"].detail
    assert "not counted as zero" in by_source["prh"].detail
    assert by_source["brreg"].state == "live"
    assert result.candidates[0].name == "HAVNIO AS"


def test_live_search_never_caches_what_was_typed(monkeypatch, live):
    seen = []

    def fake_get(url, **kwargs):
        seen.append(kwargs)
        raise httpx.ConnectError("no network in tests")

    monkeypatch.setattr(net, "get", fake_get)
    for register in (prh, brreg, rik):
        assert register.search_result("meriva").status.state == "unavailable"
    assert len(seen) == 3 and all(k["use_cache"] is False and k["timeout_s"] <= 10 for k in seen)


def _prh_company(
    business_id: str,
    names: list[tuple[str, str, str | None]],
    *,
    ended: str | None = None,
    situations: tuple[str, ...] = (),
) -> dict:
    """A YTJ v3 company in the shape PRH answers a name search with: (name, type, end date) per name."""
    return {
        "businessId": {"value": business_id, "registrationDate": "2001-05-04"},
        "names": [{"name": n, "type": t, "endDate": end} for n, t, end in names],
        "companyForms": [{"type": "16", "descriptions": [{"languageCode": "3", "description": "Limited company"}]}],
        "tradeRegisterStatus": "4" if ended else "1",
        "endDate": ended,
        "companySituations": [{"type": s} for s in situations],
    }


def test_name_rank_ignores_diacritics():
    assert name_rank("Wartsila", "Wärtsilä Oyj Abp") == 0
    assert name_rank("wärtsilä", "WARTSILA GREECE") == 1
    assert name_rank("Meyer Group", "Meyer Group OÜ") == 0  # OÜ is a legal-form word with or without the dots


def test_prh_status_says_ceased_bankrupt_or_registered():
    assert (
        prh.parse_company(_prh_company("0820663-6", [("Deltamarin Oy", "1", "2009-04-30")], ended="2009-04-30")).status
        == "ceased"
    )
    assert (
        prh.parse_company(_prh_company("1234567-1", [("Konkurssi Oy", "1", None)], situations=("KONK",))).status
        == "bankrupt"
    )
    assert prh.parse_company(_prh_company("1704468-3", [("Deltamarin Oy", "1", None)])).status == "registered"


def test_a_ceased_company_never_ranks_above_a_trading_one(fake_net, live):
    fake_net.routes["opendata-ytj-api"] = {
        "companies": [
            _prh_company("0820663-6", [("Deltamarin Oy", "1", "2009-04-30")], ended="2009-04-30"),
            _prh_company("1704468-3", [("Deltamarin Oy", "1", None), ("Delta-Sigma Oy", "1", "2009-04-29")]),
        ]
    }
    found = search.search("Deltamarin", "FI").candidates
    assert [(c.business_id, c.status, c.closed) for c in found] == [
        ("1704468-3", "registered", False),
        ("0820663-6", "ceased", True),
    ]


def test_a_former_or_trading_name_finds_the_company_under_its_current_name(fake_net, live):
    fake_net.routes["opendata-ytj-api"] = {
        "companies": [
            _prh_company(
                "1937107-1",
                [
                    ("Railo Technology Oy", "1", None),
                    ("Aker Arctic Technology Oy", "1", "2026-02-16"),
                    ("Railo Technology Ab", "2", None),
                ],
            ),
            _prh_company(
                "3515482-7", [("Arctic Marine Technology Group Oy", "1", None), ("Aker Arctic Technology", "3", None)]
            ),
        ]
    }
    result = search.search("Aker Arctic", "FI")
    railo, other = (next(c for c in result.candidates if c.business_id == i) for i in ("1937107-1", "3515482-7"))
    assert (railo.name, railo.formerly) == ("Railo Technology Oy", "Aker Arctic Technology Oy")
    assert other.also_known_as == "Aker Arctic Technology" and other.formerly is None
    assert "former_names" not in result.model_dump_json()


def test_norwegian_double_branches_collapse_and_associations_come_last(fake_net, live):
    def entity(orgnr: str, name: str, form: str) -> dict:
        return {"organisasjonsnummer": orgnr, "navn": name, "organisasjonsform": {"kode": form}}

    fake_net.routes["/enheter"] = {
        "_embedded": {
            "enheter": [
                entity("900000001", "KONGSBERG HØYRE", "FLI"),
                entity("900000002", "KONGSBERG MARITIME LTD", "UTLA"),
                entity("900000003", "KONGSBERG MARITIME LTD", "NUF"),
                entity("900000004", "KONGSBERG MARITIME AS", "AS"),
            ]
        }
    }
    found = [(c.name, c.form) for c in search.search("Kongsberg", "NO").candidates if not c.company_id]
    assert found == [("KONGSBERG MARITIME AS", "AS"), ("KONGSBERG MARITIME LTD", "NUF"), ("KONGSBERG HØYRE", "FLI")]
    assert "FLI" not in fake_net.calls[-1].params["organisasjonsform"]  # the register is asked for businesses only


def test_a_lookup_flags_a_ceased_company_as_closed(fake_net, live):
    fake_net.routes["opendata-ytj-api"] = {
        "companies": [_prh_company("0820663-6", [("Deltamarin Oy", "1", "2009-04-30")], ended="2009-04-30")]
    }
    result = lookup.lookup("FI", "0820663-6")
    assert result.found and result.closed and result.registry.status == "ceased"
    fake_net.routes["opendata-ytj-api"] = {"companies": [_prh_company("1704468-3", [("Deltamarin Oy", "1", None)])]}
    assert not lookup.lookup("FI", "1704468-3").closed
