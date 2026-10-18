"""Replay what the sources showed between two dates, from recorded snapshots and fixtures only (never live).

Event dates are the sources' own dates; first_seen_at is when the data was recorded. Signals without a real
date (some recorded award notices) are left out rather than given one.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from bluewatch.models import Signal
from bluewatch.sources import brreg, cordis, prh, rik, ted
from bluewatch.sources.common import in_window


def replay(start: date, end: date) -> list[Signal]:
    founded = (
        prh.fetch_new_companies(start, end, offline=True).signals
        + brreg.fetch_new_companies(start, end, offline=True).signals
        + brreg.fetch_updates(datetime(start.year, start.month, start.day, tzinfo=timezone.utc), offline=True).signals
        + rik.fetch_new_companies(start, end).signals
    )
    dated = prh.recorded_share_issues() + ted.recorded_notices() + cordis.load_projects()
    founded = [s for s in founded if s.event_date is None or s.event_date <= end]
    signals = {s.id: s for s in founded + [s for s in dated if in_window(s.event_date, start, end)]}
    return sorted(signals.values(), key=lambda s: (s.event_date or start, s.id))
