"""Claims from a company's own page, each with a quote that is literally on the page.

The model only extracts; every claim is then checked here. Dropped: quotes not on the page, claims with a
number their quote does not hold, contact details, and team claims that are not counts or roles (team
evidence never carries a person's name).
Nothing is taken from a refused or truncated response.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from bluewatch.llm import ModelClient, ModelRequest
from bluewatch.models import Company, Evidence
from bluewatch.read.fetch import Page
from bluewatch.read.prompts import CLAIM_FIELDS, EXTRACT_SCHEMA, EXTRACT_SYSTEM, ask_json, page_block
from bluewatch.read.quotecheck import normalise, numbers_in_quote, quote_in_any

MAX_PER_FIELD = 3
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"(?<!\w)(?:\+|0)\d[\d\s()-]{6,}\d")
_COUNT = re.compile(
    r"\d+|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|dozen|kaksi|kolme|neljä|viisi|"
    r"kuusi|två|tre|fyra|fem|fire|kaks|kolm|neli|viis)\b",
    re.I,
)
# Roles a team claim may name. Words like "team" or "staff" only count together with a number.
ROLE_WORDS = frozenset(
    """
founder founders co-founder co-founders cofounder cofounders ceo cto coo cfo cso cmo cpo cob chair chairman
chairwoman chairperson board director directors engineer engineers developer developers scientist scientists
researcher researchers designer designers experts expert specialists specialist advisors advisor phd phds
perustaja perustajat toimitusjohtaja hallitus asiantuntijaa insinööriä tutkijaa kehittäjää grundare vd styrelse
ingenjörer gründer gründere daglig leder asutaja asutajad juhataja
""".split()
)
# Capitalised words that start sentences in team passages without being names.
_PLAIN = frozenset(
    """
our the we us meet about founded with and of in at by a an get join contact today since led built team teams
staff people person persons employee employees members member professionals women men partners partner
meidän tiimi tiimimme työntekijää henkilöä vi vår vårt teamet anställda medarbetare personer ansatte meie
töötajad töötajat
""".split()
)


def _names_a_person(text: str, company_names: list[str], *, strict: bool) -> bool:
    """Heuristic: a role followed by a capitalised word ("CEO Matti"), or, when strict, any two
    capitalised words in a row that are not roles or the company's name ("Matti Meikäläinen")."""
    allowed = ROLE_WORDS | _PLAIN | {w.casefold() for n in company_names for w in re.findall(r"\w+", n)}
    words = re.findall(r"[^\W\d_][\w'’-]*", text)
    run = 0
    for i, word in enumerate(words):
        capitalised = word[0].isupper() and not word.isupper()
        if capitalised and word.casefold() not in allowed:
            if i > 0 and words[i - 1].casefold() in ROLE_WORDS:
                return True
            run += 1
            if strict and run >= 2:
                return True
        else:
            run = 0
    return False


def _acceptable(field: str, claim: str, value: str, quote: str, page: Page, names: list[str]) -> bool:
    texts = (claim, value, quote)
    if any(_EMAIL.search(t) or _PHONE.search(t) for t in texts):
        return False
    if not (numbers_in_quote(claim, quote) and numbers_in_quote(value, quote)):
        return False
    if any(_names_a_person(t, names, strict=field == "team") for t in texts):
        return False
    if field == "team":
        words = {w.casefold() for w in re.findall(r"[\w-]+", value)}
        if not (_COUNT.search(value) or words & ROLE_WORDS):
            return False
    return quote_in_any(quote, page.quotable())


def read_claims(
    company: Company, page: Page, model: ModelClient, *, model_id: str, retrieved_at: datetime | None
) -> tuple[list[Evidence], str | None]:
    """(product, customers, pricing, impact, funding and team claims, each quote-verified; None), or
    ([], why the model gave none we can use)."""
    if not page.ok:
        return [], f"site not read: {page.error}"
    request = ModelRequest(
        task="extract_claims",
        system=EXTRACT_SYSTEM,
        prompt=page_block(page, company.names),
        model=model_id,
        max_tokens=4096,
        json_schema=EXTRACT_SCHEMA,
    )
    data, problem = ask_json(model, request)
    if problem is None and isinstance(data.get("claims"), list):
        return _verified_claims(company, page, data["claims"], retrieved_at), None
    return [], f"model {problem or 'invalid'}"


def _verified_claims(company: Company, page: Page, items: list, retrieved_at: datetime | None) -> list[Evidence]:
    kept: list[Evidence] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        field, claim, value, quote = (str(item.get(k, "")).strip() for k in ("field", "claim", "value", "quote"))
        key = (field, normalise(value or quote))
        if field not in CLAIM_FIELDS or not claim or key in seen:
            continue
        if sum(e.field == field for e in kept) >= MAX_PER_FIELD:
            continue
        if not _acceptable(field, claim, value, quote, page, company.names):
            continue
        seen.add(key)
        digest = hashlib.sha1(f"{field}|{quote}".encode("utf-8")).hexdigest()[:8]
        kept.append(
            Evidence(
                id=f"{company.id}:site:{field}:{digest}",
                company_id=company.id,
                field=field,
                claim=claim,
                value=value or None,
                quote=quote,
                url=page.final_url,
                retrieved_at=retrieved_at,
                source_family=f"site:{page.domain}",
                tag="llm",
                verified_quote=True,
            )
        )
    return kept
