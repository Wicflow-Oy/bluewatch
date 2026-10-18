"""The status strip: one line per source saying live, daily file, cached or unavailable, and why."""

from __future__ import annotations

from collections.abc import Callable

from bluewatch.models import ConnectorResult, SourceStatus
from bluewatch.sources.common import describe_error, describe_failure, unavailable


def run(source: str, fetch: Callable[[], ConnectorResult]) -> ConnectorResult:
    """Run one connector. An exception becomes an "unavailable" status, never an empty "nothing new"."""
    try:
        return fetch()
    except Exception as exc:  # last-resort guard; each connector reports its own known failures first
        return ConnectorResult(status=unavailable(source, describe_failure(source, "call", exc)))


def strip(results: list[ConnectorResult | BaseException]) -> list[SourceStatus]:
    """Statuses for the strip. An exception in the list (from a gather) becomes "unavailable" with a plain detail."""
    return [
        item.status
        if isinstance(item, ConnectorResult)
        else unavailable(getattr(item, "source", "unknown"), describe_error(item))
        for item in results
    ]
