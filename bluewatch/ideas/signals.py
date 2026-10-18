"""The signals the rubric reads: what a team claims, each found as the exact sentence that says it.

A signal is a claim such as "names who pays" or "counted buyer conversations". The rules find each one
themselves (the first sentence that shows it) in English, Finnish or Swedish (vocabulary.py); a model
may add more in vet.py, but only with a quote that passes the same test.

Evidence and payment signals respect negation: "we haven't talked to any buyers yet" earns nothing.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from bluewatch.ideas import vocabulary as v
from bluewatch.ideas.models import Claim, ClaimField, IdeaSubmission
from bluewatch.ideas.text import sentences, word_list
from bluewatch.rules.presets import load_preset
from bluewatch.rules.text import find_phrases

IMPACT_SIGNAL = "impact_mechanism"  # found per preset: the chosen area's own words in the text
IMPACT_FIELDS: tuple[ClaimField, ...] = ("problem", "solution", "exists_detail")
SPECIFIC = re.compile(f"{v.NUMBER.pattern}|{v.MONTH.pattern}", re.I)  # a number, a count word or a month


@dataclass(frozen=True)
class Signal:
    fields: tuple[ClaimField, ...]
    text: str  # how the ledger describes the claim
    detect: Callable[[str], bool]  # the rules' own test on one sentence
    requires: Callable[[str], bool] = lambda s: True  # what any quote, including a model's, must contain
    negatable: bool = False  # a negated mention ("we have not tested it") is no claim


def negated(sentence: str, start: int) -> bool:
    """A negation cue in the few words before `start`, within the same clause."""
    before = sentence[:start]
    clause = before[max((m.end() for m in v.CLAUSE_BREAK.finditer(before)), default=0) :]
    return bool(v.NEGATION.search(" ".join(word_list(clause)[-v.NEGATION_WINDOW :])))


def says(pattern: re.Pattern[str], sentence: str) -> bool:
    """The sentence states it: at least one mention of `pattern` that is not negated."""
    return any(not negated(sentence, m.start()) for m in pattern.finditer(sentence))


def _has(pattern: re.Pattern[str]) -> Callable[[str], bool]:
    return lambda s: bool(pattern.search(s))


def _says(pattern: re.Pattern[str], also: re.Pattern[str] | None = None) -> Callable[[str], bool]:
    return lambda s: says(pattern, s) and (also is None or bool(also.search(s)))


def _specific_who(s: str) -> bool:
    return len(word_list(s)) >= 2 and not v.GENERIC_WHO.fullmatch(s.strip(" .!?"))


def _not_vague(s: str) -> bool:
    return not v.VAGUE.search(s)


def _method(s: str) -> bool:
    return bool(v.MECHANISM.search(s)) and _not_vague(s)


SIGNALS: dict[str, Signal] = {
    "named_customer": Signal(("who_has_it",), "Says who has the problem", _specific_who, _specific_who),
    "quantified_pain": Signal(
        ("problem", "who_has_it"), "Sizes the problem with a number", _has(v.NUMBER), _has(v.NUMBER)
    ),
    "why_now": Signal(("problem",), "Says why now", _has(v.WHY_NOW)),
    "mechanism": Signal(("solution",), "Says how the solution works", _method, _not_vague),
    "comparison": Signal(("solution", "problem"), "Says what it replaces or beats", _has(v.COMPARISON)),
    "payer": Signal(("who_pays", "solution"), "Names who pays or how it charges", _says(v.PAYER), negatable=True),
    "price_point": Signal(("who_pays",), "Gives a price", _says(v.NUMBER, v.CURRENCY), _has(v.NUMBER), negatable=True),
    "grant_reliance": Signal(("who_pays",), "Expects grants or donations to pay", _says(v.GRANTS), negatable=True),
    "impact_measure": Signal(
        ("problem", "solution", "exists_detail"),
        "Names an impact it would measure",
        _says(v.NUMBER, v.IMPACT_UNIT),
        _has(v.NUMBER),
    ),
    "built": Signal(("exists_detail", "solution"), "Says something is built or tested", _says(v.BUILT), negatable=True),
    "built_specific": Signal(
        ("exists_detail",),
        "Gives specifics of what was built or tested",
        _says(v.BUILT, SPECIFIC),
        _has(SPECIFIC),
        negatable=True,
    ),
    "buyer_talks": Signal(
        ("exists_detail", "problem", "who_has_it"),
        "Says they talked to potential buyers",
        _says(v.TALKS),
        negatable=True,
    ),
    "buyer_talks_counted": Signal(
        ("exists_detail", "problem", "who_has_it"),
        "Counts the buyer conversations",
        _says(v.TALKS, v.NUMBER),
        _has(v.NUMBER),
        negatable=True,
    ),
    "buyer_commitment": Signal(
        ("exists_detail", "who_pays"), "Describes a buyer's commitment", _says(v.COMMITS), negatable=True
    ),
}


def fits(signal: str, quote: str) -> bool:
    """Whether a quote, such as one a model offers, can stand for the signal. A quote for a negatable
    signal may hold no negation at all: the model gets no benefit of the doubt."""
    s = SIGNALS[signal]
    return s.requires(quote) and not (s.negatable and v.NEGATION.search(quote))


def impact_areas(preset: str) -> dict[str, list[str]]:
    """The preset's impact areas with their English words."""
    return load_preset(preset).impact.areas


def area_words(text: str, area: str, english: list[str]) -> list[str]:
    """The words in `text` that point to `area`: the preset's English ones, then Finnish and Swedish ones."""
    found = find_phrases(text, english)
    pattern = v.AREA_WORDS.get(area)
    found += [m.group(0) for m in pattern.finditer(text)] if pattern else []
    return list(dict.fromkeys(w.lower() for w in found))


def rule_claims(sub: IdeaSubmission) -> list[Claim]:
    """The claims the rules find on their own: the first sentence that shows each signal."""
    found = []
    for name, signal in SIGNALS.items():
        for field_name in signal.fields:
            quote = next((s for s in sentences(getattr(sub, field_name)) if signal.detect(s)), None)
            if quote:
                found.append(Claim(field=field_name, signal=name, quote=quote))
                break
    areas = impact_areas(sub.preset)
    if sub.impact_area in areas:
        for field_name in IMPACT_FIELDS:
            quote = next(
                (
                    s
                    for s in sentences(getattr(sub, field_name))
                    if area_words(s, sub.impact_area, areas[sub.impact_area])
                ),
                None,
            )
            if quote:
                found.append(Claim(field=field_name, signal=IMPACT_SIGNAL, quote=quote))
                break
    return found


def inferred_areas(sub: IdeaSubmission) -> dict[str, list[str]]:
    """Impact areas the text points to besides the chosen one, with the words that point there."""
    text = " ".join(getattr(sub, f) for f in ("title", *IMPACT_FIELDS))
    found = {
        area: area_words(text, area, english)
        for area, english in impact_areas(sub.preset).items()
        if area != sub.impact_area
    }
    return {area: hits for area, hits in found.items() if hits}
