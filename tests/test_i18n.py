"""Translated responses: prose fields change language, evidence and identifiers never do."""

from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from bluewatch import i18n
from bluewatch.api.app import app
from bluewatch.models import Reason, SourceStatus

TABLE = {
    "Register record found": "Rekisteritieto löytyi",
    "Kelluu Oy": "never used: names are not translated",
    "https://kelluu.com/": "never used: urls are not translated",
    "Act now": "Toimi nyt",
}


@pytest.fixture
def finnish(monkeypatch):
    monkeypatch.setattr(i18n, "table", lambda lang: {} if lang == "en" else TABLE)


def test_translates_prose_fields_only(finnish):
    data = {
        "name": "Kelluu Oy",
        "url": "https://kelluu.com/",
        "quote": "Register record found",
        "reasons": [{"text": "Register record found", "url": "https://kelluu.com/"}],
    }
    out = i18n.localize(data, "fi")
    assert out == {
        "name": "Kelluu Oy",
        "url": "https://kelluu.com/",
        "quote": "Register record found",
        "reasons": [{"text": "Rekisteritieto löytyi", "url": "https://kelluu.com/"}],
    }


def test_falls_back_to_english_and_keeps_english_as_is(finnish):
    assert i18n.localize({"why": ["Not in the table"]}, "fi") == {"why": ["Not in the table"]}
    data = {"why": ["Register record found"]}
    assert i18n.localize(data, "en") is data


def test_label_maps_translate_values_never_keys(finnish):
    out = i18n.localize({"group_labels": {"act_now": "Act now"}}, "fi")
    assert out == {"group_labels": {"act_now": "Toimi nyt"}}


def test_invitation_text_keeps_its_own_language(finnish):
    out = i18n.localize({"invite": {"message": "Register record found", "note": "Register record found"}}, "fi")
    assert out == {"invite": {"message": "Register record found", "note": "Rekisteritieto löytyi"}}


def test_models_come_back_as_the_same_model(finnish):
    reason = Reason(text="Register record found", source_label="Kelluu Oy", url="https://kelluu.com/")
    out = i18n.localize([reason], "fi")[0]
    assert isinstance(out, Reason)
    assert (out.text, out.url) == ("Rekisteritieto löytyi", "https://kelluu.com/")
    status = SourceStatus(source="prh", label="Act now", state="live", detail="Not in the table")
    assert i18n.localize(status, "fi").model_dump() == {**status.model_dump(), "label": "Toimi nyt"}


def test_api_takes_a_language_and_refuses_unknown_ones():
    client = TestClient(app)
    assert client.get("/api/meta?lang=fi").status_code == 200
    assert client.get("/api/meta?lang=de").status_code == 422


def test_one_pattern_covers_every_number_and_moves_them_where_the_language_needs(finnish, monkeypatch):
    table = {
        "Deadline {0} Oct {1}, in {2} days": "Määräaika {0}.10.{1}, {2} päivän päästä",
        "#{0} would be Awake.AI at {1}, below #{2}": "Sijalla {0} olisi Awake.AI ({1}), sijan {2} jälkeen",
        "Grant signed {0}-{1}-{2}": "Avustus allekirjoitettu {2}.{1}.{0}",
    }
    monkeypatch.setattr(i18n, "table", lambda lang: table)
    assert i18n.localize_text("Deadline 31 Oct 2026, in 13 days", "fi") == "Määräaika 31.10.2026, 13 päivän päästä"
    assert i18n.localize_text("#11 would be Awake.AI at 0.5796, below #10", "fi") == (
        "Sijalla 11 olisi Awake.AI (0,5796), sijan 10 jälkeen"
    )
    assert i18n.localize_text("Grant signed 2026-03-05", "fi") == "Avustus allekirjoitettu 05.03.2026"
    assert i18n.localize_text("Deadline 31 Oct 2026, today", "fi") == "Deadline 31 Oct 2026, today"  # no pattern


def test_numbers_inside_names_codes_and_dotted_dates_stay_text():
    assert i18n.pattern("Lab2Impact cuts CO2 by 12,000.5 t (checked 17.10.2026; v2.1)") == (
        "Lab2Impact cuts CO2 by {0} t (checked 17.10.2026; v2.1)",
        ["12,000.5"],
    )
    assert i18n.pattern("EUR 1,500,000 for 3 of 4") == ("EUR {0} for {1} of {2}", ["1,500,000", "3", "4"])


def test_codes_and_licence_versions_keep_their_dots_while_quantities_take_the_comma(monkeypatch):
    table = {
        "Industry code {0} (Fishing services) (Brreg)": "Toimialakoodi {0} (kalastuspalvelut) (Brreg)",
        "Seaweed company (Brreg NACE {0}), score {1}": "Merileväyritys (Brreg NACE {0}), pisteet {1}",
        "Sources: PRH (CC BY {0}), {1} rows": "Lähteet: PRH (CC BY {0}), {1} riviä",
    }
    monkeypatch.setattr(i18n, "table", lambda lang: table)
    assert i18n.localize_text("Industry code 03.300 (Fishing services) (Brreg)", "fi") == (
        "Toimialakoodi 03.300 (kalastuspalvelut) (Brreg)"
    )
    assert i18n.localize_text("Seaweed company (Brreg NACE 03.211), score 0.58", "fi") == (
        "Merileväyritys (Brreg NACE 03.211), pisteet 0,58"
    )
    assert i18n.localize_text("Sources: PRH (CC BY 4.0), 12,000 rows", "fi") == (
        "Lähteet: PRH (CC BY 4.0), 12\u00a0000 riviä"
    )


def test_swedish_prose_names_finnish_towns_in_swedish_and_leaves_organisation_names_alone():
    assert i18n.swedish_town_names("Grundat 11.10.2019 i Turku; Säte: Vaasa (PRH)") == (
        "Grundat 11.10.2019 i Åbo; Säte: Vasa (PRH)"
    )
    for name in (
        "Meyer Turku Oy deltar",
        "Koordinator: University of Turku",
        "deltar i Helsinki Blue Economy Studio",
        "Grundat i Jyväskylä",
    ):
        assert i18n.swedish_town_names(name) == name
    assert i18n.localize_text("A Rauma boat builder", "sv") == "En båtbyggare i Raumo"
    assert i18n.localize_text("A Rauma boat builder", "fi") == "Raumalainen veneenrakentaja"


def _slots(text: str) -> set[str]:
    return set(re.findall(r"\{\d+\}", text))


def test_every_source_pattern_is_translated_with_the_same_slots():
    source = json.loads((i18n.I18N_DIR / "source.json").read_text(encoding="utf-8"))["strings"]
    for lang in ("fi", "sv"):
        table = i18n.table(lang)
        missing = [text for text in source if text not in table]
        assert not missing, f"{lang}: {len(missing)} patterns without a translation, e.g. {missing[:3]}"
        lost = [text for text, translated in table.items() if _slots(text) != _slots(translated)]
        assert not lost, f"{lang}: slots differ in {len(lost)} translations, e.g. {lost[:3]}"


@pytest.mark.parametrize(
    ("lang", "path"),
    [
        ("fi", "/api/alerts?mode=apelago"),
        ("fi", "/api/alerts?mode=redstone"),
        ("sv", "/api/list?mode=apelago"),
        ("sv", "/api/list?mode=redstone"),
    ],
)
def test_a_later_day_still_reads_fully_translated(monkeypatch, lang, path):
    """The table is collected on one day; countdowns, ages and dates on another day still find their pattern."""
    monkeypatch.setenv("BLUEWATCH_TODAY", "2026-10-30")
    prose: list[str] = []
    i18n.walk(TestClient(app).get(path).json(), lambda text: prose.append(text) or text)
    untranslated = [text for text in prose if text.strip() and i18n.pattern(text)[0] not in i18n.table(lang)]
    assert prose and not untranslated, f"{len(untranslated)} of {len(prose)} fall back to English: {untranslated[:3]}"
