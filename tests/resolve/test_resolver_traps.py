"""The ten entity-resolution traps (T1–T10), one test each.

Pass rule: return the gold entity as resolved/probable, or ambiguous/unconfirmed with the gold among the
first three candidates, or abstain where nothing is resolvable keylessly. Failing = accepting a company
that is not the gold. Registry rows are as recorded from the registers; sole traders (natural persons) and
the person-named partnership are replaced by synthetic records with valid checksums.
"""

import pytest

from bluewatch.models import Candidate, Registry
from bluewatch.resolve.resolver import company_from, resolve

ACCEPTS = ("resolved", "probable")

KELLUU = Registry(country="FI", id="2902007-2", name="Kelluu Oy", municipality="Joensuu")
KELLUU_CLOTHING = Registry(country="FI", id="3431445-4", name="Kelluu Clothing Oy")
WOLTTER = Registry(country="FI", id="0877777-0", name="Woltter Ky")  # the real Ky carries a person's name
SEABER = Registry(country="FI", id="2855258-7", name="Seaber Oy", website="seaber.io")
SEABERRY = Registry(country="FI", id="3558526-4", name="Seaberry Oy", website="seaberry.io")
SEABERGS = Registry(country="FI", id="2018415-0", name="Seabergs Ab")
CLEWAT = Registry(country="FI", id="2896110-2", name="Clewat Oy", website="www.clewat.com")
ATLAN = Registry(country="FI", id="3480010-2", name="Atlan Studio Oy")
NORSEPOWER_FI = Registry(country="FI", id="2506251-5", name="Norsepower Oy Ltd", website="www.norsepower.com")
NORSEPOWER_NO = Registry(country="NO", id="936106404", name="NORSEPOWER AS")
HYKE_AS = Registry(country="NO", id="912288161", name="HYKE AS")
HYKE_ENK_1 = Registry(country="NO", id="910000004", name="HYKE SOLE TRADER ONE", form="ENK", natural_person=True)
HYKE_ENK_2 = Registry(country="NO", id="922345678", name="HYKE SOLE TRADER TWO", form="ENK", natural_person=True)
HYKA_DRIFT = Registry(country="NO", id="934691342", name="SD DRIFT & VEDLIKEHOLD HYKA")


def ids(resolution):
    return [c.registry.id for c in resolution.candidates]


def test_t1_kelluu_is_ambiguous_with_kelluu_oy_listed_first():
    r = resolve("Kelluu", country="FI", candidates=[KELLUU_CLOTHING, KELLUU])
    assert r.state == "ambiguous"
    assert ids(r)[:2] == [KELLUU.id, KELLUU_CLOTHING.id]


def test_t2_wolt_never_becomes_woltter():
    r = resolve("Wolt", country="FI", candidates=[WOLTTER])
    assert r.state in ("ambiguous", "unresolved")
    assert all(c.score == 0 for c in r.candidates)  # listed only as a rejected near-name


def test_t3_seaber_is_probable_on_its_own_site_with_namesakes_listed():
    r = resolve("Seaber", country="FI", domain="seaber.io", candidates=[SEABERGS, SEABERRY, SEABER])
    assert r.state == "probable"
    assert ids(r)[0] == SEABER.id
    assert {SEABERRY.id, SEABERGS.id} <= set(ids(r))


def test_t3_seaberrys_site_is_never_accepted_for_seaber():
    r = resolve("Seaber", country="FI", domain="seaberry.io", candidates=[SEABERGS, SEABERRY, SEABER])
    assert r.state not in ACCEPTS
    assert ids(r)[0] == SEABER.id
    assert "seaberry.io" in r.reason


def test_t4_hyke_is_ambiguous_and_never_lists_sole_traders():
    r = resolve("Hyke", country="NO", domain="hyke.no", candidates=[HYKE_AS, HYKE_ENK_1, HYKE_ENK_2, HYKA_DRIFT])
    assert r.state == "ambiguous"
    assert ids(r)[0] == HYKE_AS.id
    assert not any(c.registry.natural_person for c in r.candidates)
    assert "paste" in r.reason and "hyke.no is not linked" in r.reason


def test_t5_clewat_with_a_failing_certificate_is_unconfirmed():
    r = resolve(
        "Clewat", country="FI", site_note="www.clewat.com: the site's TLS certificate fails", candidates=[CLEWAT]
    )
    assert r.state == "unconfirmed"
    assert ids(r) == [CLEWAT.id]
    assert "TLS certificate" in r.reason


def test_t6_swedish_company_without_registry_is_unresolved_with_the_reason():
    r = resolve("Echandia", country="SE", site_note="echandia.se: HTTP 429")
    assert r.state == "unresolved"
    assert "no keyless SE registry" in r.reason and "429" in r.reason


def test_t7_danish_company_without_vat_on_the_page_is_unresolved():
    r = resolve("Blue Ocean Robotics", country="DK", domain="blueoceanrobotics.com")
    assert r.state == "unresolved"
    assert "no keyless DK registry" in r.reason


def test_t8_edilm_page_owned_by_atlan_studio_is_flagged_not_accepted():
    r = resolve("Edilm", country="FI", domain="atlan.fi", page_ids=["FI:3480010-2"], candidates=[ATLAN])
    assert r.state == "unconfirmed"
    assert ids(r) == [ATLAN.id]
    assert "does not match" in r.reason


def test_t8_edilm_with_the_packs_id_is_flagged_not_accepted():
    r = resolve("Edilm", country="FI", registry_id="3480010-2", domain="atlan.fi", candidates=[ATLAN])
    assert r.state == "unconfirmed"
    assert ids(r) == [ATLAN.id]
    assert "does not match 'Edilm'" in r.reason


def test_t9_norsepower_keeps_finland_primary_and_lists_norway_without_merging():
    r = resolve("Norsepower", country="FI", registry_id="2506251-5", candidates=[NORSEPOWER_NO, NORSEPOWER_FI])
    assert r.state == "resolved"
    assert ids(r) == [NORSEPOWER_FI.id, NORSEPOWER_NO.id]
    assert "not merged" in r.candidates[1].reason
    company = company_from(NORSEPOWER_FI, r)
    assert company.id == "FI:2506251-5"
    assert company.names == ["Norsepower Oy Ltd"]


def test_t9_url_input_with_tracking_tail_resolves_through_the_registry_website():
    r = resolve(
        "Norsepower",
        country="FI",
        domain="https://www.norsepower.com/?utm_source=x",
        candidates=[NORSEPOWER_FI, NORSEPOWER_NO],
    )
    assert r.state == "probable"
    assert ids(r)[0] == NORSEPOWER_FI.id


def test_t10_a_namesake_site_abroad_is_not_attached():
    r = resolve("Seaber", country="FI", domain="seaber.com", candidates=[SEABER])
    assert r.state == "unconfirmed"
    assert "seaber.com is not linked" in r.reason


@pytest.mark.parametrize("given, state", [("2855258-7", "resolved"), ("1234567-8", "unresolved")])
def test_business_id_fast_path_and_bad_checksum(given, state):
    r = resolve("", country="FI", registry_id=given, candidates=[SEABER])
    assert r.state == state
    if state == "unresolved":
        assert "fails the FI business ID checksum" in r.reason


def test_vat_and_own_id_on_the_site_resolve():
    assert resolve("Seaber", country="FI", vat_id="FI28552587", candidates=[SEABER]).state == "resolved"
    on_site = resolve(
        "Seaber", country="FI", domain="seaber.io", page_ids=["VAT:FI28552587"], candidates=[SEABERRY, SEABER]
    )
    assert on_site.state == "resolved" and ids(on_site)[0] == SEABER.id


def test_a_valid_id_with_a_different_name_needs_confirmation():
    r = resolve("Seaberry", country="FI", registry_id="2855258-7", candidates=[SEABER])
    assert r.state == "probable"


def test_sole_traders_are_never_resolved_or_turned_into_companies():
    r = resolve("Hyke", country="NO", registry_id=HYKE_ENK_1.id, candidates=[HYKE_ENK_1])
    assert r.state == "unresolved" and r.candidates == []
    with pytest.raises(ValueError):
        company_from(HYKE_ENK_1, r)


def test_auxiliary_names_match_and_are_kept_on_the_company():
    store = Registry(country="FI", id="3197621-7", name="Sub Marine Store Oy")
    aux = Candidate(name="Suomen Varavirta", registry=store, score=0.0, reason="PRH auxiliary name")
    r = resolve("Suomen Varavirta", country="FI", candidates=[aux])
    assert r.state == "unconfirmed" and ids(r) == [store.id]
    assert company_from(store, r).names == ["Sub Marine Store Oy", "Suomen Varavirta"]
