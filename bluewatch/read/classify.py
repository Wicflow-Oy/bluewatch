"""Is this an ocean or water company? A model answer with a verified quote, or the offline reader.

A blue answer whose quote is not on the page is shown as "not blue": the claim has no evidence.
When the model is unavailable (no key, budget spent, refusal, truncated or broken output) the keyword
reader answers instead and `fallback` says why, so the card can show it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from bluewatch.llm import ModelClient, ModelRequest
from bluewatch.models import Company, Evidence, Vertical
from bluewatch.read.fetch import Page
from bluewatch.read.keywords import classify_keywords
from bluewatch.read.prompts import CLASSIFY_SCHEMA, CLASSIFY_SYSTEM, VERTICALS, ask_json, page_block
from bluewatch.read.quotecheck import quote_in_any

VERTICAL_LABELS = {
    "maritime_ports": "maritime and ports",
    "ocean_infra_clean_energy": "ocean infrastructure and clean energy",
    "marine_intelligence": "marine intelligence",
    "blue_biotech_water": "blue biotech and water",
    "other": "other ocean or water",
}


@dataclass
class Classification:
    blue: bool
    vertical: Vertical | None
    quote: str | None
    verified_quote: bool
    reason: str
    method: Literal["model", "keywords", "none"]
    model_id: str | None = None
    fallback: str | None = None  # why the keyword reader answered instead of the model


def classify_offline(page: Page, *, company_names=(), fallback: str | None = None) -> Classification:
    result = classify_keywords(page.quotable(), company_names=company_names)
    # Cut from the page, so this should always hold; checked anyway, like every other quote.
    verified = result.quote is not None and quote_in_any(result.quote, page.quotable())
    reason = result.reason if fallback is None else f"{result.reason} (offline keyword reader: {fallback})"
    return Classification(
        result.blue and verified,
        result.vertical if verified else None,
        result.quote,
        verified,
        reason,
        method="keywords",
        fallback=fallback,
    )


def classify_blue(
    page: Page, model: ModelClient | None, *, model_id: str, company_names: list[str] | tuple[str, ...] = ()
) -> Classification:
    if not page.ok:
        return Classification(False, None, None, False, f"The page could not be read: {page.error}.", method="none")
    if model is None:
        return classify_offline(page, company_names=company_names, fallback="no model configured")
    request = ModelRequest(
        task="classify_blue",
        system=CLASSIFY_SYSTEM,
        prompt=page_block(page, company_names),
        model=model_id,
        max_tokens=2048,
        json_schema=CLASSIFY_SCHEMA,
    )
    data, problem = ask_json(model, request)
    if problem is None and not _well_formed(data):
        problem = "invalid"
    if problem is not None:
        return classify_offline(page, company_names=company_names, fallback=f"model {problem}")
    quote = data["quote"].strip() or None
    verified = bool(quote) and quote_in_any(quote, page.quotable()) and not _only_names(quote, company_names)
    blue = data["blue"] and verified
    reason = data["reason"].strip()
    if data["blue"] and not verified:
        reason = f"Not shown as blue: the model's quote is not on the page. ({reason})"
    vertical = data["vertical"] if blue and data["vertical"] in VERTICALS else None
    return Classification(blue, vertical, quote, verified, reason, method="model", model_id=model_id)


def _well_formed(data: dict) -> bool:
    return (
        isinstance(data.get("blue"), bool)
        and isinstance(data.get("quote"), str)
        and isinstance(data.get("reason"), str)
        and data.get("vertical") in [*VERTICALS, "none"]
    )


def _only_names(quote: str, names) -> bool:
    """A quote that is just the company's name ("Blue Ocean Robotics") proves nothing about the business."""
    q = quote.casefold().strip(" .|-")
    return any(q == n.casefold().strip() for n in names)


def classification_evidence(
    company: Company, page: Page, result: Classification, *, retrieved_at: datetime | None
) -> Evidence | None:
    """Ocean or water work as evidence, when its quote is verified on the page. A "not ocean work" answer is a
    judgement no quote can show, so it never becomes a claim; the card then simply has no vertical from the site."""
    if not (result.blue and result.verified_quote and result.quote):
        return None
    claim = f"The company's site describes {VERTICAL_LABELS.get(result.vertical or 'other')} work."
    offline = result.method == "keywords"
    digest = hashlib.sha1(result.quote.encode("utf-8")).hexdigest()[:8]
    return Evidence(
        id=f"{company.id}:site:vertical:{digest}",
        company_id=company.id,
        field="vertical",
        claim=claim,
        value=result.vertical,
        quote=result.quote,
        url=page.final_url,
        retrieved_at=retrieved_at,
        source_family=f"site:{page.domain}",
        tag="site" if offline else "llm",
        verified_quote=True,
        basis=f"offline keyword reader ({result.fallback})" if offline and result.fallback else None,
    )
