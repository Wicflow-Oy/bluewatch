import json
import zipfile
from datetime import date

import pytest

from bluewatch import net, seed
from bluewatch.sources import rik
from bluewatch.sources.common import FIXTURES

HEADER = (
    "nimi;ariregistri_kood;ettevotja_oiguslik_vorm;ettevotja_oigusliku_vormi_alaliik;kmkr_nr;ettevotja_staatus;"
    "ettevotja_staatus_tekstina;ettevotja_esmakande_kpv;ettevotja_aadress;asukoht_ettevotja_aadressis;"
    "asukoha_ehak_kood;asukoha_ehak_tekstina;indeks_ettevotja_aadressis;ads_adr_id;ads_ads_oid;"
    "ads_normaliseeritud_taisaadress;teabesysteemi_link"
)


def row(name: str, code: str, form: str, status: str, first_entry: str, location: str) -> str:
    return f"{name};{code};{form};;;{status};;{first_entry};;;;{location};;;;;"


ROWS = [  # synthetic: an OÜ with codes, an OÜ without, a sole trader, an older company, a foundation
    row("Testlaev OÜ", "17000001", "Osaühing", "R", "01.10.2026", "Kesklinna linnaosa, Tallinn, Harju maakond"),
    row("Koodita OÜ", "17000002", "Osaühing", "R", "02.10.2026", "Peetri alevik, Rae vald, Harju maakond"),
    row("Mari Testinimi", "17000003", "Füüsilisest isikust ettevõtja", "R", "03.10.2026", "Tartu linn, Tartu maakond"),
    row("Vana Laevandus AS", "10000004", "Aktsiaselts", "L", "05.05.2005", "Pärnu linn, Pärnu maakond"),
    row("Meri Sihtasutus", "90000005", "Sihtasutus", "R", "04.10.2026", "Harju maakond"),
]
GENERAL = [  # the general JSON file: one company object per block of lines
    {
        "ariregistri_kood": 17000001,
        "nimi": "Testlaev OÜ",
        "yldandmed": {
            "teatatud_tegevusalad": [
                {"emtak_kood": "62011", "on_pohitegevusala": False, "lopp_kpv": None},
                {"emtak_kood": "50201", "on_pohitegevusala": True, "lopp_kpv": None},
                {"emtak_kood": "47911", "on_pohitegevusala": False, "lopp_kpv": "01.01.2026"},
            ],
            "sidevahendid": [
                {"liik": "EMAIL", "sisu": "info@testlaev.ee"},
                {"liik": "MOB", "sisu": "+372 5555 5555"},
                {"liik": "WWW", "sisu": "https://www.testlaev.ee/et"},
            ],
        },
    },
    {
        "ariregistri_kood": 17000003,
        "nimi": "Mari Testinimi",
        "yldandmed": {"teatatud_tegevusalad": [{"emtak_kood": "03121", "on_pohitegevusala": True}]},
    },
]


@pytest.fixture
def simple_zip(tmp_path):
    path = tmp_path / rik.SIMPLE_CSV
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ettevotja_rekvisiidid__lihtandmed.csv", "﻿" + "\n".join([HEADER, *ROWS]) + "\n")
    return path


@pytest.fixture
def general_zip(tmp_path):
    path = tmp_path / rik.GENERAL_JSON
    blocks = ",\n".join("    " + json.dumps(c, ensure_ascii=False, indent=4).replace("\n", "\n    ") for c in GENERAL)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ettevotja_rekvisiidid__yldandmed.json", "[\n" + blocks + "\n]\n")
    return path


def load(simple_zip, **kwargs):
    return rik.load_new_companies(date(2026, 10, 1), date(2026, 10, 16), simple_csv_zip=simple_zip, **kwargs)


def test_csv_window_skips_sole_traders_and_keeps_missing_codes_none(simple_zip):
    result = load(simple_zip)
    assert result.status.state == "daily_file"
    assert [r.id for r in result.records] == ["17000001", "17000002", "90000005"]
    assert "1 sole traders (FIE) skipped" in result.status.detail
    assert "codes are unknown, not missing" in result.status.detail
    assert all(r.industry_code is None for r in result.records)
    first = result.records[0]
    assert (first.form, first.founded, first.municipality, first.status) == (
        "OÜ",
        date(2026, 10, 1),
        "Tallinn",
        "registered",
    )
    assert result.records[1].municipality == "Rae vald"
    assert {s.entity_ref.id for s in result.signals} == {"17000001", "17000002", "90000005"}


def test_sole_trader_row_is_a_private_natural_person():
    row = dict(zip(HEADER.split(";"), ROWS[2].split(";"), strict=True))
    record = rik.registry_from_row(row)
    assert record.natural_person and record.name is None and record.form == "FIE"


def test_codes_from_the_streamed_general_file_drop_contacts(simple_zip, general_zip):
    codes = rik.stream_codes(general_zip, {"17000001"})
    assert codes == {"17000001": {"emtak": ["50201", "62011"], "website": "www.testlaev.ee"}}
    result = load(simple_zip, general_json_zip=general_zip)
    assert result.records[0].industry_code == "50201" and result.records[0].industry_scheme == "EMTAK"
    assert result.records[1].industry_code is None
    assert "@" not in result.model_dump_json() and "5555" not in result.model_dump_json()


def test_codes_from_a_cached_extract(simple_zip, tmp_path):
    cache = tmp_path / "codes.json"
    cache.write_text(json.dumps({"codes": {"17000002": {"emtak": ["30111"], "website": None}}}), encoding="utf-8")
    result = load(simple_zip, codes_cache=cache)
    assert result.records[1].industry_code == "30111"


def test_bad_file_is_unavailable(tmp_path):
    broken = tmp_path / "broken.zip"
    broken.write_bytes(b"not a zip")
    result = load(broken)
    assert result.status.state == "unavailable" and "not counted as zero" in result.status.detail


def test_recorded_extract_feeds_offline():
    result = rik.fetch_new_companies(date(2026, 10, 1), date(2026, 10, 16))
    assert result.status.state == "cached"
    assert result.records and all(r.country == "EE" and not r.natural_person for r in result.records)
    assert sum(r.industry_code is not None for r in result.records) > 0.9 * len(result.records)
    outside = rik.fetch_new_companies(date(2026, 1, 1), date(2026, 1, 31))
    assert outside.status.state == "unavailable"


def test_recorded_extract_has_no_people_or_contacts():
    text = (FIXTURES / rik.RECORDED).read_text(encoding="utf-8")
    data = json.loads(text)
    forms = {row[data["columns"].index("form")] for row in data["rows"]}
    assert "FIE" not in forms and "@" not in text


def test_index_build_and_lookup(simple_zip, tmp_path, monkeypatch):
    monkeypatch.setattr(rik, "FIXTURES", tmp_path)
    assert rik.build_index(simple_zip, tmp_path / rik.INDEX) == 4  # the sole trader is not indexed
    found = rik.lookup_result("10000004", offline=True)
    assert found.status.state == "cached"
    assert (found.records[0].name, found.records[0].status) == ("Vana Laevandus AS", "in liquidation")
    assert rik.lookup("17000003", offline=True) is None


def test_lookup_in_the_recorded_index():
    record = rik.lookup("14117645", offline=True)
    assert (record.name, record.form, record.municipality) == ("Avatec Marine OÜ", "OÜ", "Tallinn")


def test_live_lookup_uses_the_register_search(fake_net):
    fake_net.routes["autocomplete"] = seed.fixture(f"sources/{rik.LIVE_SEARCH}")["response"]
    result = rik.lookup_result("14117645", offline=False)
    assert result.status.state == "live"
    assert result.records[0].name == "Avatec Marine OÜ"
    assert fake_net.calls[0].params == {"q": "14117645"}


def test_search_hit_without_a_legal_form_is_kept_private():
    hit = {
        "reg_code": 17000003,
        "name": "Mari Testinimi",
        "status": "R",
        "legal_form": "1",
        "legal_address": "Tartu maakond, Tartu linn, Rüütli 1",
    }
    record = rik.registry_from_search(hit, None)
    assert record.natural_person and record.name is None
    company = rik.registry_from_search(hit | {"name": "Testlaev Sihtasutus"}, None)
    assert not company.natural_person and company.form == "SA"


def test_lookup_validates_codes_and_reports_failures(fake_net):
    assert rik.lookup_result("1411764", offline=False).status.state == "unavailable"
    fake_net.routes["autocomplete"] = (500, {})
    failed = rik.lookup_result("14117645", offline=False)
    assert failed.status.state == "unavailable" and "HTTP 500" in failed.status.detail


def test_download_needs_online_mode():
    with pytest.raises(net.OfflineError):
        rik.download_daily_files(confirm=True)


def test_download_lists_sizes_without_confirm(monkeypatch, tmp_path, capsys):
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def head(self, url):
            return type("Head", (), {"headers": {"content-length": "18621713"}})()

    monkeypatch.setenv("BLUEWATCH_OFFLINE", "0")
    monkeypatch.setattr(rik.httpx, "Client", FakeClient)
    files = rik.download_daily_files(tmp_path)
    assert files == [(rik.SIMPLE_CSV, 18621713), (rik.GENERAL_JSON, 18621713)]
    assert "18.6 MB" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("location", "municipality"),
    [
        ("Harju maakond, Tallinn, Mustamäe linnaosa, Kadaka tee 3/2", "Tallinn"),
        ("Kesklinna linnaosa, Tallinn, Harju maakond", "Tallinn"),
        ("Kodutänav 5-12, 10111", None),  # a street and postal code are never passed on as the municipality
        ("Harju maakond", None),
    ],
)
def test_only_the_municipality_is_kept_from_an_address(location, municipality):
    assert rik._municipality(location) == municipality
