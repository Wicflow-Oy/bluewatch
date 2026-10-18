"""The offline reader: ocean and water vocabulary in Finnish, Swedish, Norwegian, Estonian and English.

Used when no model is available (no API key, the daily budget is spent, or the model refused). Every
quote is cut from the page's own text, so it passes the quote check by construction.

The company's own name is masked before matching: "Blue Ocean Robotics" sells service robots, and the
"ocean" in its name is not evidence (a plain keyword match falls for exactly that).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bluewatch.models import Vertical
from bluewatch.resolve.names import LEGAL_FORMS, fold

# Specific terms: one is enough. Word stems end in \w* for Finnish and Estonian inflection
# ("satamassa", "vesiviljelyn"). "shipping" alone is excluded: it was always "free shipping".
STRONG: dict[Vertical, list[str]] = {
    "maritime_ports": [
        r"maritime",
        r"seafarers?",
        r"shipyards?",
        r"shipbuilding",
        r"ship ?owners?",
        r"vessels?",
        r"ferr(?:y|ies)",
        r"workboats?",
        r"tugboats?",
        r"marinas?",
        r"port operators?",
        r"shipping (?:compan\w*|lines?|industry|emissions)",
        r"marine (?:vessels?|engines?|propulsion|fuels?)",
        r"merenkul\w*",
        r"laiva\w*",
        r"satam\w*",
        r"telakk\w*",
        r"lautta(?:liikente\w*|yhtiö\w*|an|oja)?",
        r"vesiliikente\w*",
        r"sjöfart\w*",
        r"fartyg\w*",
        r"hamn(?:ar|en|arna)?",
        r"färj\w*",
        r"rederi\w*",
        r"skipsfart\w*",
        r"fartøy\w*",
        r"havn(?:en|er|ene)?",
        r"verft\w*",
        r"ferj\w*",
        r"laevandus\w*",
        r"laev(?:a|ad|ade|u)?",
        r"sadam\w*",
        r"parvlaev\w*",
        r"meresõi\w*",
    ],
    "ocean_infra_clean_energy": [
        r"offshore (?:wind|energy|platforms?|installations?|renewables?)",
        r"wave (?:energy|power)",
        r"tidal (?:energy|power|stream)",
        r"floating (?:wind|solar)",
        r"ocean energy",
        r"marine (?:energy|renewables?)",
        r"subsea (?:cables?|infrastructure)",
        r"merituuli\w*",
        r"aaltovoim\w*",
        r"aaltoenergi\w*",
        r"havsvind\w*",
        r"havsbaserad vindkraft",
        r"vågkraft\w*",
        r"vågenergi\w*",
        r"havvind\w*",
        r"bølgekraft\w*",
        r"bølgeenergi\w*",
        r"meretuul\w*",
        r"avamere tuul\w*",
        r"laineenergi\w*",
    ],
    "marine_intelligence": [
        r"underwater",
        r"subsea",
        r"sonars?",
        r"bathymetr\w*",
        r"hydrograph\w*",
        r"oceanograph\w*",
        r"seabed",
        r"sea ?floor",
        r"marine (?:data|monitoring|biodiversity|research|robotics|sensors?|surveys?|conservation)",
        r"ocean (?:data|monitoring|observation|mapping|intelligence)",
        r"unmanned surface vehicles?",
        r"vedenalai\w*",
        r"merentutkimu\w*",
        r"merenpohj\w*",
        r"undervattens\w*",
        r"havsbotten\w*",
        r"havsforskning\w*",
        r"undervanns\w*",
        r"havbunn\w*",
        r"havforskning\w*",
        r"veealu\w*",
        r"merepõhj\w*",
        r"mereuuring\w*",
    ],
    "blue_biotech_water": [
        r"aquacultur\w*",
        r"fish farm\w*",
        r"seaweeds?",
        r"macroalgae",
        r"microalgae",
        r"algae",
        r"kelp",
        r"seafood",
        r"(?:marine|blue) biotech\w*",
        r"water quality",
        r"waste ?water",
        r"water treatment",
        r"water utilit\w*",
        r"drinking water",
        r"desalination",
        r"eutrophication",
        r"oil spills?",
        r"fisher(?:y|ies)",
        r"ballast water",
        r"vesiviljel\w*",
        r"kalankasvat\w*",
        r"kalanviljel\w*",
        r"jäteve\w*",
        r"vedenlaa\w*",
        r"vesilaito\w*",
        r"vedenpuhdist\w*",
        r"rehevöit\w*",
        r"vesistö\w*",
        r"öljyntorjun\w*",
        r"öljyvahin\w*",
        r"vattenbruk\w*",
        r"fiskodling\w*",
        r"avloppsvatten\w*",
        r"vattenrening\w*",
        r"vattenkvalitet\w*",
        r"övergödning\w*",
        r"oljeutsläpp\w*",
        r"havbruk\w*",
        r"fiskeoppdrett\w*",
        r"oppdrett\w*",
        r"avløpsvann\w*",
        r"vannkvalitet\w*",
        r"fiskeri\w*",
        r"vesiviljelus\w*",
        r"kalakasvatus\w*",
        r"vetika\w*",
        r"reove\w*",
        r"veekvaliteet\w*",
        r"veepuhastus\w*",
    ],
}
# Ocean terms that name no vertical: enough to say "blue", not which kind.
GENERAL = [
    r"baltic sea",
    r"itämer\w*",
    r"östersjö\w*",
    r"läänemer\w*",
    r"blue economy",
    r"sinitalou\w*",
    r"ocean (?:health|conservation|plastics?|economy)",
]
# Generic words: common on non-ocean pages too ("sea view"), so three different ones are needed.
WEAK = [
    r"seas?",
    r"oceans?",
    r"marine",
    r"ships?",
    r"boats?",
    r"ports?",
    r"harbou?rs?",
    r"fish",
    r"coastal",
    r"baltic",
    r"archipelago",
    r"meri",
    r"meren",
    r"saaristo\w*",
    r"rannikko\w*",
    r"hav",
    r"havet",
    r"skärgård\w*",
    r"kyst\w*",
    r"båt\w*",
    r"vene(?:et|en|ita|iden|ily\w*|paik\w*)?",
]
MIN_WEAK = 3
MAX_QUOTE_CHARS = 220


def _compile(terms: list[str]) -> re.Pattern:
    return re.compile(r"(?<!\w)(?:" + "|".join(terms) + r")(?!\w)", re.I)


_STRONG_RE: dict[Vertical | None, re.Pattern] = {vertical: _compile(terms) for vertical, terms in STRONG.items()}
_STRONG_RE[None] = _compile(GENERAL)
_WEAK_RE = _compile(WEAK)


@dataclass
class KeywordResult:
    blue: bool
    vertical: Vertical | None
    quote: str | None
    reason: str


def _terms(text: str) -> set[str]:
    patterns = [*_STRONG_RE.values(), _WEAK_RE]
    return {m.group(0).lower() for pattern in patterns for m in pattern.finditer(text)}


def _mask_names(text: str, names: list[str]) -> str:
    """Blank out the company's own name, keeping offsets so quotes are still cut from the original."""
    for name in names:
        words = [w for w in re.findall(r"\w+", name) if fold(w) not in LEGAL_FORMS]
        if words:
            pattern = re.compile(r"(?<!\w)" + r"\W+".join(map(re.escape, words)) + r"(?!\w)", re.I)
            text = pattern.sub(lambda m: " " * len(m.group(0)), text)
    return text


def _sentence_around(text: str, start: int, end: int) -> str:
    """The sentence holding text[start:end], cut from the original so it is an exact substring."""
    left = max(text.rfind(ch, 0, start) for ch in ".!?|\n") + 1
    rights = [i for ch in ".!?|\n" if (i := text.find(ch, end)) != -1]
    right = min(rights) + 1 if rights else len(text)
    if right - left > MAX_QUOTE_CHARS:
        left = max(left, start - MAX_QUOTE_CHARS // 2)
        right = min(right, left + MAX_QUOTE_CHARS)
        while left > 0 and text[left - 1].isalnum():
            left += 1  # don't start inside a word
        while right < len(text) and text[right].isalnum():
            right -= 1
    return text[left:right].strip(" .|\n\t")


def classify_keywords(parts: list[str], *, company_names: list[str] | tuple[str, ...] = ()) -> KeywordResult:
    """Classify a page from its quotable parts (title, descriptions, body)."""
    names = list(company_names)
    strong_hits: dict[Vertical | None, int] = {}
    first: tuple[str, int, int] | None = None
    weak: dict[str, tuple[str, int, int]] = {}
    only_in_name: set[str] = set()
    for part in filter(None, parts):
        masked = _mask_names(part, names)
        only_in_name |= _terms(part) - _terms(masked)
        for vertical, pattern in _STRONG_RE.items():
            for m in pattern.finditer(masked):
                strong_hits[vertical] = strong_hits.get(vertical, 0) + 1
                first = first or (part, m.start(), m.end())
        for m in _WEAK_RE.finditer(masked):
            weak.setdefault(fold(m.group(0)).rstrip("s"), (part, m.start(), m.end()))
    if first:
        named = {v: n for v, n in strong_hits.items() if v is not None}
        vertical = max(named, key=named.__getitem__) if named else None
        part, start, end = first
        reason = f"The page uses the ocean or water term '{part[start:end]}'."
        return KeywordResult(True, vertical, _sentence_around(part, start, end), reason)
    if len(weak) >= MIN_WEAK:
        part, start, end = next(iter(weak.values()))
        reason = f"The page uses several general ocean words ({', '.join(sorted(weak)[:4])})."
        return KeywordResult(True, None, _sentence_around(part, start, end), reason)
    if only_in_name:
        reason = "The only ocean words are in the company's own name; the page itself has no ocean or water terms."
        return KeywordResult(False, None, None, reason)
    return KeywordResult(False, None, None, "No ocean or water terms on the page.")
