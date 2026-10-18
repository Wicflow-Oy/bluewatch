"""Builders for small, readable rule tests."""

from __future__ import annotations

from datetime import date, datetime, timezone
from itertools import count

from bluewatch.models import Company, Evidence, Registry, Resolution

AT = datetime(2026, 10, 17, tzinfo=timezone.utc)
_ids = count(1)


def company(
    cid: str = "FI:1234567-8",
    *,
    name: str = "Testi Oy",
    vertical: str | None = "maritime_ports",
    founded: date | None = date(2026, 9, 1),
    one_liner: str | None = None,
    tags: list[str] | None = None,
    natural_person: bool = False,
    country: str | None = None,
) -> Company:
    cc, _, reg_id = cid.partition(":")
    return Company(
        id=cid,
        names=[name],
        registry=Registry(
            country=country or cc, id=reg_id, name=name, founded=founded, form="OY", natural_person=natural_person
        ),
        vertical=vertical,
        resolution=Resolution(state="resolved", reason="test"),
        one_liner=one_liner,
        tags=tags or [],
    )


def ev(
    claim: str,
    *,
    field: str = "product",
    tag: str = "read",
    state: str = "fact",
    family: str = "research_pack",
    cid: str = "FI:1234567-8",
    event_date: date | None = None,
    value: str | None = None,
    why_unknown: str | None = None,
) -> Evidence:
    return Evidence(
        id=f"{cid}#t{next(_ids)}",
        company_id=cid,
        field=field,
        claim=claim,
        tag=tag,
        state=state,
        source_family=family,
        event_date=event_date,
        value=value,
        why_unknown=why_unknown,
        first_seen_at=AT,
        retrieved_at=AT,
    )


def registered(cid: str = "FI:1234567-8", when: date = date(2026, 9, 1)) -> Evidence:
    return ev(
        f"Registered {when:%d %b %Y} (PRH)",
        field="founded",
        tag="registry",
        family="prh",
        cid=cid,
        event_date=when,
        value=when.isoformat(),
    )
