"""Company names and domains: normal forms and word-boundary matching.

Matching is on whole words only. A substring match accepts "Seaberry Oy" for "Seaber" because "seaber" is a
substring of "seaberry"; here that is a different word, never a match.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal
from urllib.parse import urlsplit

# Legal forms are stripped only at the start or end of a name ("Oy Lokala Ab"), never from the
# middle, so a word like "as" inside a name survives.
LEGAL_FORMS = frozenset(
    "oy oyj ab abp ky ay tmi osakeyhtio aktiebolag as asa ans da enk nuf ou fie mtu aps a/s "
    "ltd limited inc llc gmbh plc bv nv sa srl kb hb".split()
)
_FOLD = str.maketrans({"ø": "o", "æ": "ae", "ß": "ss", "đ": "d", "ł": "l", "þ": "th"})

MatchLevel = Literal["exact", "partial", "near", "none"]


def fold(s: str) -> str:
    """Lower case without diacritics: 'Wärtsilä' → 'wartsila', 'Sjøfart' → 'sjofart'."""
    s = unicodedata.normalize("NFKD", (s or "").lower().translate(_FOLD))
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def name_words(name: str) -> list[str]:
    """Words of a company name without leading or trailing legal forms."""
    words = re.findall(r"[a-z0-9]+(?:/[a-z]+)?", fold(name))
    while words and words[-1] in LEGAL_FORMS:
        words.pop()
    while words and words[0] in LEGAL_FORMS:
        words.pop(0)
    return [w for part in words for w in part.split("/") if w]


def match_level(query: str, candidate: str) -> MatchLevel:
    """How a registry name matches the name we were given.

    exact:   the same words ("Seaber" / "Seaber Oy"; also "Emission Eye" / "Emission-Eye")
    partial: one name's words appear whole inside the other ("Kelluu" / "Kelluu Clothing Oy")
    near:    only a substring of a longer word ("Wolt" / "Woltter Ky"): a different name
    none:    nothing in common
    """
    q, c = name_words(query), name_words(candidate)
    if not q or not c:
        return "none"
    if q == c or "".join(q) == "".join(c):
        return "exact"
    if _contains(c, q) or _contains(q, c):
        return "partial"
    if "".join(q) in "".join(c) or "".join(c) in "".join(q):
        return "near"
    return "none"


def _contains(longer: list[str], shorter: list[str]) -> bool:
    n = len(shorter)
    return any(longer[i : i + n] == shorter for i in range(len(longer) - n + 1))


def phrase_pattern(name: str) -> re.Pattern | None:
    """A regex for the name's words as a whole-word phrase, to search folded text with."""
    words = name_words(name)
    if not words:
        return None
    return re.compile(r"(?<![a-z0-9])" + r"[\W_]*".join(map(re.escape, words)) + r"(?![a-z0-9])")


def name_on_page(name: str, text: str) -> bool:
    pattern = phrase_pattern(name)
    return bool(pattern and pattern.search(fold(text)))


def domain_of(url_or_host: str | None) -> str | None:
    """'https://www.Norsepower.com/about?utm_source=x' → 'norsepower.com'."""
    raw = (url_or_host or "").strip().lower()
    if not raw:
        return None
    host = urlsplit(raw if "//" in raw else f"//{raw}").hostname or ""
    host = host.removeprefix("www.")
    return host if "." in host else None


def same_site(a: str | None, b: str | None) -> bool:
    """Same host, ignoring www. and subdomains of the same registrable domain."""
    da, db = domain_of(a), domain_of(b)
    if not da or not db:
        return False
    return da == db or da.endswith("." + db) or db.endswith("." + da)


GUESS_TLDS = {"FI": (".fi", ".com", ".io"), "NO": (".no", ".com", ".io"), "EE": (".ee", ".com", ".eu")}


def domain_guesses(name: str, country: str) -> list[str]:
    """Hostnames worth trying for a company with no registered website."""
    words = name_words(name)
    if not words:
        return []
    bases = ["".join(words)] + (["-".join(words)] if len(words) > 1 else [])
    tlds = GUESS_TLDS.get(country.upper(), (".com",))
    return [base + tld for base in bases for tld in tlds]
