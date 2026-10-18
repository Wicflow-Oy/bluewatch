"""The anti-hallucination check: a quote counts only if it is literally on the page, and a claim only if its
numbers are in its quote.

Normalisation removes only typography (Unicode forms, case, whitespace, curly quotes, dash variants,
zero-width characters). There is no fuzzy matching: a paraphrase is not a quote.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

# Written as code points so the invisible ones (no-break and zero-width spaces) stay visible here.
_TYPOGRAPHY = {
    **dict.fromkeys([0x2018, 0x2019, 0x201A, 0x201B], "'"),  # curly single quotes
    **dict.fromkeys([0x201C, 0x201D, 0x201E, 0x00AB, 0x00BB], '"'),  # curly double quotes, guillemets
    **dict.fromkeys([*range(0x2010, 0x2016), 0x2212], "-"),  # hyphens, dashes, minus
    0x00A0: " ",  # no-break space
    **dict.fromkeys([0x200B, 0x200C, 0x200D, 0xFEFF], None),  # zero-width characters
}
# A single word on a page proves nothing ("sea" is on half the web); quotes need some substance.
MIN_WORDS = 2
MIN_CHARS = 8


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").translate(_TYPOGRAPHY).casefold()
    return re.sub(r"\s+", " ", text).strip()


def quote_in_page(quote: str, page_text: str) -> bool:
    """True when the normalised quote is a substring of the normalised page text."""
    q = normalise(quote).strip(" .,;:!?\"'")
    if len(q) < MIN_CHARS or len(q.split()) < MIN_WORDS:
        return False
    return q in normalise(page_text)


def quote_in_any(quote: str, texts: Iterable[str]) -> bool:
    """Checked part by part (title, descriptions, body), so a quote can't straddle two of them."""
    return any(quote_in_page(quote, t) for t in texts if t)


def numbers_in_quote(text: str, quote: str) -> bool:
    """True when every number in `text` (a claim or its value) is also in the quote. A quote that exists on the page
    proves nothing about a number taken from elsewhere on it ("local expertise in 20 countries" quoting
    "Delivering local expertise wherever your vessels operate")."""
    quoted = set(re.findall(r"\d+", normalise(quote)))
    return all(number in quoted for number in re.findall(r"\d+", normalise(text)))
