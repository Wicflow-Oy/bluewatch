"""The public live lookup: a visitor types a business ID (FI, NO or EE).

Nothing the visitor enters is stored, logged or sent anywhere except the official register for that
country. Sole traders are natural persons: the lookup confirms only that the ID belongs to a sole
trader and shows nothing else. When the register can't answer, the result says so; it never claims
"not found".
"""

from __future__ import annotations

import importlib
import re
from typing import Literal

from pydantic import BaseModel

from bluewatch.models import Registry, SourceStatus
from bluewatch.sources.common import go_live, is_closed, not_trading

LookupCountry = Literal["FI", "NO", "EE"]
_SOURCE = {"FI": "prh", "NO": "brreg", "EE": "rik"}
_FORMAT_HELP = {
    "FI": "A Finnish business ID looks like 1234567-8.",
    "NO": "A Norwegian organisation number has 9 digits.",
    "EE": "An Estonian registry code has 8 digits.",
}


class LookupResult(BaseModel):
    country: LookupCountry
    business_id: str
    found: bool
    natural_person: bool = False
    registry: Registry | None = None
    closed: bool = False  # the register lists the company as ceased, deleted, bankrupt or being wound up
    company_id: str | None = None  # set when the company is in the precomputed set
    status: SourceStatus
    recorded_only: bool = False  # live lookups are off here: only the recorded register data was searched
    message: str = ""


def normalise(country: str, raw: str) -> str | None:
    from bluewatch.resolve.ids import normalise_id

    return normalise_id(country, re.sub(r"[\s.]", "", raw or ""))


def _precomputed_id(country: str, business_id: str) -> str | None:
    from bluewatch import demo

    cid = f"{country}:{business_id}"
    return cid if cid in demo.build().companies else None


def lookup(country: str, raw_id: str) -> LookupResult:
    country = country.upper()
    if country not in _SOURCE:
        raise ValueError("Only Finnish, Norwegian and Estonian business IDs are supported.")
    business_id = normalise(country, raw_id)
    if not business_id:
        raise ValueError(_FORMAT_HELP[country])
    # The connector decides live vs recorded (BLUEWATCH_LIVE_LOOKUPS) and reports which in its status.
    result = importlib.import_module(f"bluewatch.sources.{_SOURCE[country]}").lookup_result(business_id)
    recorded_only = not go_live(None, lookup=True)
    base = {
        "country": country,
        "business_id": business_id,
        "status": result.status,
        "recorded_only": recorded_only,
        "company_id": _precomputed_id(country, business_id),
    }
    if not result.records:
        found = base["company_id"] is not None
        if recorded_only:
            message = "Live register lookups are off in this workspace, and this ID is not in the recorded data."
        elif result.status.state == "unavailable":
            message = f"The register couldn't answer: {result.status.detail}."
        else:
            message = "No company with this ID in the register."
        return LookupResult(found=found, message="" if found else message, **base)
    registry = result.records[0]
    if registry.natural_person:
        return LookupResult(
            found=True,
            natural_person=True,
            **{**base, "company_id": None},
            message="This ID belongs to a sole trader (a private person), so no details are shown.",
        )
    if is_closed(registry.status):
        return LookupResult(found=True, registry=registry, closed=True, message=closed_message(registry.status), **base)
    return LookupResult(found=True, registry=registry, **base)


def closed_message(status: str) -> str:
    return f"The company is {not_trading(status)}, so no programmes, investors or next steps are shown."
