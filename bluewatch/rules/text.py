"""Small text and date helpers shared by the rules. Matching is on word boundaries, so "sea" never
matches "research" and "seaber" never matches "seaberry"."""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date
from functools import lru_cache


def norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text or "")).strip().lower()


@lru_cache(maxsize=4096)
def _phrase_re(phrase: str) -> re.Pattern[str]:
    return re.compile(r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)")


def find_phrases(text: str, phrases: list[str] | tuple[str, ...]) -> list[str]:
    """The phrases that occur in text as whole words, in the order given."""
    t = norm(text)
    return [p for p in phrases if _phrase_re(p).search(t)]


# Data keys whose words alone would read wrongly; every other key just loses its underscores.
KEY_WORDS = {"data_digital": "data and digital", "aquaculture_food": "aquaculture and food"}
_KEY = re.compile(r"\b[a-z0-9]+(?:_[A-Za-z0-9]+)+\b")


def humanise_keys(text: str) -> str:
    """Data keys inside prose read as words: "Theme fit: data_digital" -> "Theme fit: data and digital"."""
    return _KEY.sub(lambda m: KEY_WORDS.get(m.group(0), m.group(0).replace("_", " ")), text)


def trunc(value: float, digits: int = 2) -> str:
    """Floors, never rounds: a score of 0.975 reads "0.97" and an age of 8.9 years reads "8", never higher."""
    factor = 10**digits
    # The slack keeps float error from flooring 0.29 to 0.28 (0.29 * 100 = 28.999999999999996).
    return f"{math.floor(value * factor + 1e-9) / factor:.{digits}f}"


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


_DATE = re.compile(r"(?<!\d)(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?(?!\d)")


def parse_date(text: str | None) -> date | None:
    """A full ISO date at the start of text; partial dates ("2026-06", "2012") are not dates."""
    m = _DATE.match((text or "").strip())
    if not m or not (m.group(2) and m.group(3)):
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def approx_date(text: str | None) -> date | None:
    """Day, month or year precision, for ages and recency only: "2026-06" -> 1 Jun, "2012" -> 1 Jul."""
    m = _DATE.search(text or "")
    if not m:
        return None
    year, month, day = int(m.group(1)), m.group(2), m.group(3)
    if not 1900 <= year <= 2100:
        return None
    try:
        return date(year, int(month) if month else 7, int(day) if day else 1)
    except ValueError:
        return None


def years_between(start: date, end: date) -> float:
    return round((end - start).days / 365.25, 2)
