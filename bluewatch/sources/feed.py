"""New companies from Finland, Norway and Estonia in one list. Sole traders (natural persons) never leave here."""

from __future__ import annotations

from datetime import date

from bluewatch.models import Registry, Signal, SourceStatus
from bluewatch.sources import brreg, prh, rik, status


def new_companies(since: date, until: date) -> tuple[list[Registry], list[Signal], list[SourceStatus]]:
    """Records and newly_founded signals for FI + NO + EE, and one status per register for the strip."""
    results = [
        status.run("prh", lambda: prh.fetch_new_companies(since, until)),
        status.run("brreg", lambda: brreg.fetch_new_companies(since, until)),
        status.run("rik", lambda: rik.fetch_new_companies(since, until)),
    ]
    people = {r.id for result in results for r in result.records if r.natural_person}
    records = [r for result in results for r in result.records if not r.natural_person]
    signals = [s for result in results for s in result.signals if s.entity_ref.id not in people]
    return records, signals, status.strip(results)
