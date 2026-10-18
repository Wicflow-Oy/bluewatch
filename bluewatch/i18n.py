"""Translated API responses: the rules write English, and the API boundary swaps in Finnish or Swedish.

The tables in data/i18n/{fi,sv}.json map an English sentence pattern to its translation. A pattern is
the English text with each number replaced by a numbered slot ("Deadline {0} Oct {1}, in {2} days"), so
one entry covers every count, score, ID and date the rules can put in that sentence, on any day and for
any company. A translation uses the same slots, in whatever order its language needs, and the numbers
go back in with the language's decimal comma; a code keeps its dots ("Industry code 03.300").
scripts/collect_strings.py lists every pattern that needs a translation (data/i18n/source.json).

Only fields that hold our own prose are translated. Names, programme titles, quotes, URLs, IDs, enum
keys and dates stay as they are, and a string whose pattern is missing from a table stays in English.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Literal, TypeVar, cast

from fastapi import Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from bluewatch.config import DATA_DIR

Lang = Literal["en", "fi", "sv"]
LangParam = Annotated[Lang, Query(description="Language of the response's prose: en, fi or sv.")]

I18N_DIR = DATA_DIR / "i18n"

# Fields whose string (or list of strings) is prose the rules or the API wrote.
TRANSLATABLE_FIELDS = frozenset(
    {
        "action",
        "ai_read_off_note",
        "ai_read_text",
        "anonymised_name",
        "anti_gaming",
        "areas",
        "attribution",
        "base_rate_note",
        "baseline_name",
        "basis",
        "caveat",
        "caveats",
        "checked",
        "claim",
        "consent_text",
        "deadline_note",
        "deciding_rule",
        "description",
        "detail",
        "evidence_rule",
        "expected",
        "explanation",
        "facts",
        "fit_label",
        "funding_note",
        "got",
        "group_rule",
        "hint",
        "how",
        "impact_areas",
        "label",
        "list_name",
        "message",
        "next_action",
        "note",
        "notes",
        "offer",
        "one_liner",
        "organisation",
        "points",
        "potential_rule",
        "privacy_note",
        "question",
        "questions",
        "raise_by",
        "reader_note",
        "reason",
        "reasons",
        "reference",
        "rule",
        "rung_label",
        "rungs",
        "sample_label",
        "source_label",
        "stage",
        "strengths",
        "text",
        "tier_label",
        "tier_rule",
        "tier_rules",
        "unknown_reason",
        "upgrade_path",
        "vertical_note",
        "why",
        "why_here",
        "why_not_next",
        "why_these",
        "why_unknown",
    }
)
# Maps from a key to its display label (/api/meta): every string inside them is translated, keys never.
LABEL_FIELDS = frozenset({"group_labels", "tier_labels", "level_labels", "dimension_labels"})
# Text written for someone outside the team keeps its own language: an invitation goes to the
# organiser as drafted, whatever language the reader works in.
KEEP_ORIGINAL = {"invite": frozenset({"message"})}

# A number in prose: digits with optional thousands commas and decimals ("12,000", "0.5796"). Digits
# inside a word or code ("CO2", "Lab2Impact") and dotted dates or versions ("17.10.2026") stay text.
NUMBER = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?(?!\.?\d)")
# A number named as a code or a licence version is an identifier: it fills its slot as written, so
# "Industry code 03.300" and "CC BY 4.0" never get a decimal comma and read as quantities.
IDENTIFIER_BEFORE = re.compile(r"(?:\b[Cc]ode|\bNACE|\bCC BY) $")
SLOT = re.compile(r"\{(\d+)\}")

# Swedish prose names a Finnish town by its Swedish name ("Grundat i Åbo", "Säte: Vasa"), as Finland-Swedish
# readers expect: the official name in a bilingual municipality, the established one elsewhere. Only a town
# after "i" or "Säte:" and not followed by more of a name is a place; organisation names keep their own
# form ("Meyer Turku Oy", "University of Turku", "i Helsinki Blue Economy Studio").
SWEDISH_TOWN_NAMES = {
    "Espoo": "Esbo",
    "Eurajoki": "Euraåminne",
    "Hamina": "Fredrikshamn",
    "Hanko": "Hangö",
    "Helsinki": "Helsingfors",
    "Hämeenlinna": "Tavastehus",
    "Ii": "Ijo",
    "Inkoo": "Ingå",
    "Kaarina": "S:t Karins",
    "Kauniainen": "Grankulla",
    "Kemiönsaari": "Kimitoön",
    "Kirkkonummi": "Kyrkslätt",
    "Kokkola": "Karleby",
    "Kristiinankaupunki": "Kristinestad",
    "Lahti": "Lahtis",
    "Lappeenranta": "Villmanstrand",
    "Lohja": "Lojo",
    "Loviisa": "Lovisa",
    "Maarianhamina": "Mariehamn",
    "Mikkeli": "S:t Michel",
    "Naantali": "Nådendal",
    "Närpiö": "Närpes",
    "Oulu": "Uleåborg",
    "Parainen": "Pargas",
    "Pietarsaari": "Jakobstad",
    "Pori": "Björneborg",
    "Porvoo": "Borgå",
    "Pyhtää": "Pyttis",
    "Raasepori": "Raseborg",
    "Raisio": "Reso",
    "Rauma": "Raumo",
    "Sipoo": "Sibbo",
    "Tammisaari": "Ekenäs",
    "Tampere": "Tammerfors",
    "Tornio": "Torneå",
    "Turku": "Åbo",
    "Uusikaupunki": "Nystad",
    "Vaasa": "Vasa",
    "Vantaa": "Vanda",
    "Virolahti": "Vederlax",
}
SWEDISH_TOWN = re.compile(r"(\bi |Säte: )(%s)\b(?! [A-ZÅÄÖ])" % "|".join(SWEDISH_TOWN_NAMES))

T = TypeVar("T")
Translate = Callable[[str], str]


@lru_cache(maxsize=None)
def table(lang: Lang) -> dict[str, str]:
    """The English-to-`lang` table; empty for English. The Swedish one names Finnish towns in Swedish."""
    if lang == "en":
        return {}
    entries: dict[str, str] = json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    if lang == "sv":
        return {key: swedish_town_names(text) for key, text in entries.items()}
    return entries


def swedish_town_names(text: str) -> str:
    """Swedish prose with each Finnish town by its Swedish name (see SWEDISH_TOWN_NAMES)."""
    return SWEDISH_TOWN.sub(lambda town: town.group(1) + SWEDISH_TOWN_NAMES[town.group(2)], text)


def localize(obj: T, lang: Lang) -> T:
    """A copy of a response with its prose in `lang`; anything not in the table stays English."""
    if lang == "en":
        return obj
    return translated(obj, lambda text: localize_text(text, lang))


def pattern(text: str) -> tuple[str, list[str]]:
    """The table key for `text` and the numbers it held: ("Deadline {0} Oct {1}", ["31", "2026"])."""
    numbers = NUMBER.findall(text)
    slots = iter(range(len(numbers)))
    return NUMBER.sub(lambda _: f"{{{next(slots)}}}", text), numbers


def localize_text(text: str, lang: Lang) -> str:
    """One string of our own prose in `lang`, or as it is when the table has no entry for its pattern."""
    if lang == "en":
        return text
    found = table(lang).get(pattern(text)[0])
    if found is None:
        return text
    local = [local_number(text, match) for match in NUMBER.finditer(text)]
    return SLOT.sub(lambda slot: local[int(slot.group(1))], found)


def local_number(text: str, match: re.Match[str]) -> str:
    """A number of `text` with the decimal comma (12 000, 0,5796); an identifier stays as written (03.300)."""
    if IDENTIFIER_BEFORE.search(text, 0, match.start()):
        return match.group()
    return match.group().replace(",", "\u00a0").replace(".", ",")


def translated(obj: T, translate: Translate) -> T:
    """Applies `translate` to every translatable string; models come back as the same model type."""
    if isinstance(obj, BaseModel):
        return cast(T, type(obj).model_validate(walk(obj.model_dump(mode="json"), translate)))
    if isinstance(obj, list):
        return cast(T, [translated(item, translate) for item in obj])
    return cast(T, walk(jsonable_encoder(obj), translate))


def walk(value: object, translate: Translate, *, field: str | None = None, label_map: bool = False) -> object:
    """JSON data with `translate` applied where the field name allows it (see TRANSLATABLE_FIELDS)."""
    if isinstance(value, str):
        return translate(value) if label_map or field in TRANSLATABLE_FIELDS else value
    if isinstance(value, list):
        return [walk(item, translate, field=field, label_map=label_map) for item in value]
    if isinstance(value, dict):
        kept = KEEP_ORIGINAL.get(field or "", frozenset())
        return {
            key: walk(child, translate, field=None if key in kept else key, label_map=label_map or key in LABEL_FIELDS)
            for key, child in value.items()
        }
    return value
