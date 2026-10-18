"""Rank bridges per company by deadline x fit x evidence, at most three, with the parts shown."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from bluewatch.bridges.common import FIT, norm_name, party_key, strong_share
from bluewatch.bridges.generators import generate_all
from bluewatch.bridges.seed import seed_bridges
from bluewatch.models import Bridge

# Seed bridges were joined by hand, so their confidence stands in for the join quality.
SEED_FIT = {"verified": FIT["exact"], "probable": FIT["partial"], "possible": FIT["inferred"]}
CONFIDENCE_ORDER = {"verified": 0, "probable": 1, "possible": 2}


def urgency(deadline: date | None, today: date) -> float:
    """1.0 inside 45 days, stepping down to 0.5 beyond a year; no deadline at all scores 0.4."""
    if deadline is None:
        return 0.4
    days = (deadline - today).days
    if days < 0:
        return 0.0
    if days <= 45:
        return 1.0
    if days <= 120:
        return 0.8
    return 0.6 if days <= 365 else 0.5


def rank_parts(bridge: Bridge, today: date) -> dict[str, float]:
    parts = {
        "deadline": urgency(bridge.deadline, today),
        "fit": bridge.rank_parts.get("fit", SEED_FIT[bridge.confidence]),
        "evidence": round(strong_share(bridge), 3),
    }
    parts["score"] = round(parts["deadline"] * parts["fit"] * parts["evidence"], 3)
    if bridge.deadline:
        parts["days_left"] = float((bridge.deadline - today).days)
    return parts


def _same(seeded: Bridge, generated: Bridge) -> bool:
    """A generated bridge repeats a seed bridge: same type and company, same counterparty or source."""
    if seeded.type != generated.type or party_key(seeded.company) != party_key(generated.company):
        return False
    a, b = set(norm_name(seeded.counterparty.name).split()), set(norm_name(generated.counterparty.name).split())
    urls = {e.url for e in seeded.evidence_counterparty if e.url}
    return a <= b or b <= a or bool(urls & {e.url for e in generated.evidence_counterparty})


@lru_cache(maxsize=4)
def all_bridges(today: date) -> tuple[Bridge, ...]:
    """The seed bridges plus every generated bridge that does not repeat one of them."""
    seeds = seed_bridges()
    generated = [g for g in generate_all(today=today) if not any(_same(s, g) for s in seeds)]
    return tuple(seeds + generated)


def for_company(company_id: str, *, today: date, limit: int = 3, mode: str | None = None) -> list[Bridge]:
    """The top bridges for one company (or research team) key; expired deadlines are dropped."""
    ranked = []
    for bridge in all_bridges(today):
        if party_key(bridge.company) != company_id or (mode and bridge.mode not in (mode, "both")):
            continue
        parts = rank_parts(bridge, today)
        if parts["deadline"] > 0:
            ranked.append(bridge.model_copy(update={"rank_parts": parts}))
    ranked.sort(
        key=lambda b: (
            -b.rank_parts["score"],
            b.deadline or date.max,
            CONFIDENCE_ORDER[b.confidence],
            b.id,
        )
    )
    return ranked[:limit]
