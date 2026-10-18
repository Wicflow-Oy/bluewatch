import re

from bluewatch import seed
from bluewatch.rules.seed_adapter import company_and_evidence, demo_items


def _items():
    return {c.id: (c, ev, sig) for c, ev, sig in demo_items()}


def test_every_pack_company_once_including_the_curated_list():
    items = _items()
    assert len(items) == len(demo_items())
    assert {"FI:3652359-1", "NO:938525420", "FI:3101791-3"} <= set(items)  # Meriva, HAVNIO, Alpo


def test_meriva_carries_the_hand_verified_gap_ledger():
    row = next(r for r in seed.load("demo_list_2026_10_12")["rows"] if r["name"] == "Meriva Oy")
    company, evidence, signals = company_and_evidence(row)
    assert company.id == "FI:3652359-1"
    states = [e.state for e in evidence]
    assert (states.count("fact"), states.count("assumption"), states.count("unknown")) == (4, 1, 4)
    assert any(e.state == "not_applicable" and e.field == "trl" for e in evidence)
    unknown = next(e for e in evidence if e.field == "team")
    assert unknown.next_check and unknown.next_check.question
    assert [s.type for s in signals] == ["newly_founded"]


def test_share_issues_count_filing_dates_not_notice_rows():
    company, evidence, signals = _items()["FI:2506251-5"]  # Norsepower: 105 notice rows
    issues = [s for s in signals if s.type == "share_issue"]
    assert 0 < len(issues) == len({s.event_date for s in issues}) < 20
    assert all(s.sensitivity == "founder_sensitive" for s in issues)


def test_ted_awards_become_signals_and_ted_tagged_evidence():
    _, evidence, signals = _items()["FI:3101791-3"]
    awards = [e for e in evidence if e.field == "public_contracts" and e.tag == "ted"]
    assert len(awards) == 3 and all(e.url.startswith("https://ted.europa.eu/") for e in awards)
    assert sum(s.type == "award" for s in signals) == 3


def test_search_summaries_are_assumptions_never_facts():
    snippets = [e for _, ev, _ in demo_items() for e in ev if e.tag == "snippet"]
    assert snippets and all(e.state == "assumption" for e in snippets)


def test_answer_keys_never_leak_into_evidence():
    claims = {e.claim for _, ev, _ in demo_items() for e in ev}
    for row in seed.load("startups")["startups"]:
        key = row.get("answer_key") or {}
        for text in (key.get("trl_evidence"), key.get("brl_evidence"), key.get("reason")):
            assert not text or text not in claims


def test_registry_links_are_human_pages_not_raw_api_json():
    urls = [e.url for _, ev, _ in demo_items() for e in ev if e.tag == "registry" and e.url]
    assert urls and not any("opendata-ytj-api" in u or "/api/enheter" in u for u in urls)


def test_country_codes_are_iso_or_xx_for_unknown():
    countries = {c.registry.country for c, _, _ in demo_items()}
    assert all(len(cc) == 2 and cc.isalpha() and cc.isupper() for cc in countries)
    danish_vat = _items()["DK:43378015"][0]  # OceanWide Seaweed ApS, known by its VAT number DK43378015
    assert danish_vat.registry.id == "43378015"


def test_answer_keys_hold_no_people():
    keys = seed.load("answer_keys")
    assert "redstone_people_nordics" not in keys["judge_known_redstone"]
    assert not any("founder_per_redstone" in c for c in keys["judge_known_redstone"]["companies"])


def test_how_the_list_run_found_a_company_is_not_evidence_about_it():
    evidence = [e for _, ev, _ in demo_items() for e in ev]
    assert not [e for e in evidence if e.field == "discovery" or "caught it" in e.claim or "keywords missed" in e.claim]
    bases = {e.basis for e in evidence if e.field == "assessment_note"}
    assert bases == {"Analyst note in the research pack"}  # never "demo list"


def test_control_companies_carry_their_register_records():
    items = _items()
    mowi, wartsila, kongsberg = (items[cid][0].registry for cid in ("NO:964118191", "FI:0128631-1", "NO:979750730"))
    assert (mowi.form, mowi.founded.year, mowi.employees) == ("ASA", 1992, 2913)
    assert (wartsila.form, wartsila.founded.year) == ("OYJ", 1978)
    assert (kongsberg.form, kongsberg.founded.year, kongsberg.employees) == ("AS", 1998, 3681)


def test_certificate_dates_read_as_days_not_iso():
    claims = [e.claim for _, ev, _ in demo_items() for e in ev if "(crt.sh)" in e.claim]
    assert claims and not [c for c in claims if re.search(r"\d{4}-\d{2}-\d{2}", c)]


def test_founding_claims_write_whole_days_as_prose_and_never_a_note_as_a_town():
    items = _items()
    claims = [e.claim for _, evidence, _ in items.values() for e in evidence if e.field == "founded"]
    assert claims and not any(re.search(r"\d{4}-\d{2}-\d{2}|\bin see\b", claim) for claim in claims)
    assert "Founded 21 Sep 2016" in {e.claim for e in items["EE:14117645"][1]}  # the pack's "2016-09-21"
    assert items["FI:3491873-3"][0].registry.municipality is None  # the list says "see PRH"
