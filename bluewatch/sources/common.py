"""Helpers shared by the connectors: when to call a live service, signals, statuses, dates and privacy."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx
from pydantic import Field

from bluewatch import net
from bluewatch.config import FIXTURES_DIR, settings
from bluewatch.labels import SOURCE_LABELS
from bluewatch.models import (
    ConnectorResult,
    EntityRef,
    Registry,
    Signal,
    SignalSource,
    SignalType,
    SourceState,
    SourceStatus,
)

log = logging.getLogger(__name__)
FIXTURES = FIXTURES_DIR / "sources"
LIVE_FIXTURES = FIXTURES / "live_2026-10-17"
NOT_ZERO = "not counted as zero"
SEARCH_TIMEOUT_S = 8.0  # a visitor is waiting on a name search; a slow register is reported, not waited for

# What the registers call a company that no longer trades (PRH, Brreg and RIK words in one vocabulary).
CLOSED_STATUSES = frozenset({"ceased", "deleted", "bankrupt", "in liquidation", "winding up"})

# Keys that hold contact details in register responses. They are never read or recorded.
CONTACT_KEYS = {"epostadresse", "telefon", "mobil", "email", "e-mail", "phone", "telephone", "mobile", "fax"}


class NamedRecord(Registry):
    """A name-search hit that also carries the register's other names for the company, so a search for the name
    people still use finds it. Only the search reads them; serialised as a Registry, they never leave the API."""

    former_names: list[str] = Field(default_factory=list)
    other_names: list[str] = Field(default_factory=list)  # parallel and auxiliary (trading) names in use


def is_closed(status: str | None) -> bool:
    return status in CLOSED_STATUSES


def not_trading(status: str) -> str:
    """How prose says that the register lists a company as closed: "no longer trading (register status: bankrupt)"."""
    return f"no longer trading (register status: {status})"


class SourceError(RuntimeError):
    """A service answered, but not with usable data. The message is shown to users as is."""


def go_live(offline: bool | None, *, lookup: bool = False) -> bool:
    """An explicit offline=False wins; otherwise go live when the app runs online, or for lookups when allowed."""
    if offline is not None:
        return not offline
    conf = settings()
    return not conf.offline or (lookup and conf.live_lookups)


def now() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(value) -> date | None:
    """ISO (2026-10-16, 2026-10-16+02:00, 2026-10-16T06:00Z), Estonian (16.10.2026) or compact (20261016)."""
    text = str(value or "").strip()
    for fmt, size in (("%Y-%m-%d", 10), ("%d.%m.%Y", 10), ("%Y%m%d", 8)):
        try:
            return datetime.strptime(text[:size], fmt).date()
        except ValueError:
            continue
    return None


def fixture_time(text: str) -> datetime:
    """Recording times are stored as ISO strings with an offset."""
    return datetime.fromisoformat(text)


def check(resp: net.CachedResponse) -> net.CachedResponse:
    if resp.status >= 400:
        raise SourceError(f"the service answered HTTP {resp.status}")
    return resp


def describe_failure(source: str, operation: str, exc: BaseException) -> str:
    """describe_error, also logged as a warning so a failed live call leaves a trace on the server. Only the
    source, the operation and the plain description are logged, never what a visitor asked for."""
    reason = describe_error(exc)
    log.warning("%s %s failed: %s", source, operation, reason)
    return reason


def describe_error(exc: BaseException) -> str:
    """Plain words for the status strip; never raw response bodies."""
    if isinstance(exc, SourceError):
        return str(exc)
    if isinstance(exc, net.OfflineError):
        return "offline and no recorded data"
    if isinstance(exc, httpx.TimeoutException):
        return "timed out"
    if isinstance(exc, httpx.HTTPError):
        return "could not reach the service"
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return "unexpected response format"
    if isinstance(exc, OSError):
        return "could not read the local file"
    return f"failed ({type(exc).__name__})"


def source_status(
    source: str,
    state: SourceState,
    *,
    records: int | None = None,
    detail: str = "",
    data_as_of: datetime | None = None,
) -> SourceStatus:
    return SourceStatus(
        source=source,
        label=SOURCE_LABELS.get(source, source),
        state=state,
        checked_at=now(),
        data_as_of=data_as_of,
        records=records,
        detail=detail,
    )


def unavailable(source: str, reason: str) -> SourceStatus:
    return source_status(source, "unavailable", detail=f"{reason}; {NOT_ZERO}")


def failed(source: str, operation: str, exc: BaseException) -> SourceStatus:
    """The status for a failed live call, e.g. "lookup timed out; not counted as zero", logged as well."""
    return unavailable(source, f"{operation} {describe_failure(source, operation, exc)}")


def make_signal(
    source: SignalSource,
    type_: SignalType,
    ref: EntityRef,
    *,
    key: str,
    event_date: date | None,
    first_seen_at: datetime,
    url: str | None = None,
    title: str | None = None,
    payload: dict | None = None,
) -> Signal:
    payload = payload or {}
    content = json.dumps([type_, ref.id, ref.project_url, str(event_date), payload], sort_keys=True, default=str)
    return Signal(
        id=f"{source}:{key}:{type_}",
        source=source,
        type=type_,
        entity_ref=ref,
        event_date=event_date,
        first_seen_at=first_seen_at,
        url=url,
        hash=hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
        title=title,
        payload=payload,
    )


def private_person(record: Registry) -> Registry:
    """Sole traders are people: keep only what is needed to refuse showing them (no name, place or site)."""
    return Registry(country=record.country, id=record.id, form=record.form, natural_person=True)


def drop_contacts(obj):
    """Remove contact fields (e-mail, phone) before anything is written to a fixture."""
    if isinstance(obj, dict):
        return {k: drop_contacts(v) for k, v in obj.items() if k.lower() not in CONTACT_KEYS}
    if isinstance(obj, list):
        return [drop_contacts(v) for v in obj]
    return obj


# Legal-form words, so "Meriva" is an exact match for "Meriva Oy" and "HAVNIO" for "HAVNIO AS".
LEGAL_FORM_WORDS = {
    "oy",
    "oyj",
    "ab",
    "abp",
    "as",
    "asa",
    "ou",
    "osauhing",
    "aktsiaselts",
    "ky",
    "ay",
    "ry",
    "rf",
    "ltd",
    "aps",
}


def _name_words(text: str) -> list[str]:
    """Words without case or diacritics, so "Wartsila" typed on an English keyboard matches "Wärtsilä"."""
    letters = unicodedata.normalize("NFKD", text.casefold())
    return re.findall(r"\w+", "".join(c for c in letters if not unicodedata.combining(c)))


def name_rank(query: str, name: str | None) -> int | None:
    """How well a register name matches what was typed, best first: 0 the same name, 1 starts with the typed words,
    2 starts with the typed text, 3 every typed word starts a word of the name, 4 contains it; None for no match.
    Registers search loosely (HAVNIO also finds HAVINO), so their hits are re-checked here."""
    typed, words = _name_words(query), _name_words(name or "")
    if not typed or not words:
        return None
    phrase, full = " ".join(typed), " ".join(words)
    if words == typed or [w for w in words if w not in LEGAL_FORM_WORDS] == typed:
        return 0
    if words[: len(typed)] == typed:
        return 1
    if full.startswith(phrase):
        return 2
    if all(any(w.startswith(t) for w in words) for t in typed):
        return 3
    return 4 if phrase in full else None


def in_window(day: date | None, since: date, until: date) -> bool:
    return day is not None and since <= day <= until


def span_label(start: date, end: date) -> str:
    if start == end:
        return f"{start.day} {start:%b %Y}"
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day}–{end.day} {end:%b %Y}"
    return f"{start.day} {start:%b}–{end.day} {end:%b %Y}"


@dataclass(frozen=True)
class Recording:
    """One recorded file of register data and what it covers."""

    path: str  # relative to data/fixtures/sources
    start: date
    end: date
    complete: bool  # every company in the window, or only a sample
    recorded_at: datetime
    what: str  # "all limited companies registered", "blue and tech candidates registered", ...

    def exists(self) -> bool:
        return (FIXTURES / self.path).exists()

    def overlaps(self, since: date, until: date) -> bool:
        return self.start <= until and since <= self.end


def recorded_detail(recordings: list[Recording], since: date, until: date) -> str:
    """Say exactly which days the recorded data covers, so a gap never reads as 'nothing new'."""
    parts = [f"{r.what} {span_label(r.start, r.end)}" for r in recordings]
    covered = {r.start + timedelta(days=i) for r in recordings if r.complete for i in range((r.end - r.start).days + 1)}
    days = (until - since).days + 1
    if any(since + timedelta(days=i) not in covered for i in range(days)):
        parts.append(f"other days in the window were not fully recorded ({NOT_ZERO})")
    return "recorded data: " + "; ".join(parts)


def with_live_failure(result: ConnectorResult, exc: BaseException) -> ConnectorResult:
    """A failed live call falls back to recorded data, and the status says so."""
    reason = describe_failure(result.status.source, "live call", exc)
    status = result.status.model_copy(update={"detail": f"live call {reason}; {result.status.detail}"})
    return result.model_copy(update={"status": status})
