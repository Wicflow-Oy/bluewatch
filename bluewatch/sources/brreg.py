"""Norway: Brønnøysund Enhetsregisteret open API (entities and the change stream), keyless.

Calls skip the shared disk cache: Brreg responses carry company e-mail and phone fields, which are never stored.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime, timezone
from functools import lru_cache

from bluewatch import net, seed
from bluewatch.models import ConnectorResult, EntityRef, Registry, Signal, SourceState
from bluewatch.sources.common import (
    CONTACT_KEYS,
    FIXTURES,
    SEARCH_TIMEOUT_S,
    Recording,
    check,
    failed,
    fixture_time,
    go_live,
    in_window,
    make_signal,
    name_rank,
    now,
    parse_date,
    private_person,
    recorded_detail,
    source_status,
    span_label,
    unavailable,
    with_live_failure,
)

SOURCE = "brreg"
API = "https://data.brreg.no/enhetsregisteret/api"
PAGE_SIZE = 500
MAX_PAGES = 20  # the API serves at most 10,000 rows per query
UPDATE_PAGES = 5
SEARCH_SIZE = 50  # the name search is loose (HAVNIO also finds HAVINO), so read a page and re-rank
# The name search asks for businesses only: "Kongsberg" otherwise fills the page with clubs and associations (FLI).
SEARCH_FORMS = "AS,ASA,NUF,ANS,DA,KS,SA,SE,SF,BA"
MAX_WATCH_LOOKUPS = 20  # one polite lookup per watched organisation that changed
LIVE_DAY = "live_2026-10-17/brreg_enheter_2026-10-16.json"
LIVE_UPDATES = "live_2026-10-17/brreg_updates_2026-10-16.json"
LIVE_LOOKUP = "live_2026-10-17/brreg_lookup_938525420.json"
ORGNR = re.compile(r"^\d{9}$")

RECORDINGS = [
    Recording(
        LIVE_DAY,
        date(2026, 10, 16),
        date(2026, 10, 16),
        True,
        fixture_time("2026-10-17T20:34:00+03:00"),
        "all new limited companies (AS) registered",
    ),
    Recording(
        "brreg_weekly_2026-09-14_4w.json",
        date(2026, 9, 14),
        date(2026, 10, 11),
        False,
        fixture_time("2026-10-17T00:30:35+03:00"),
        "blue candidates among new AS registered",
    ),
]


# --------------------------------------------------------------------------- parsing
def _status(raw: dict) -> str:
    if raw.get("slettedato"):
        return "deleted"
    if raw.get("konkurs"):
        return "bankrupt"
    if raw.get("underAvvikling") or raw.get("underTvangsavviklingEllerTvangsopplosning"):
        return "winding up"
    return "registered"


def parse_entity(raw: dict) -> Registry:
    """One entity from the API. ENK (enkeltpersonforetak) is a person and comes back without details."""
    form = (raw.get("organisasjonsform") or {}).get("kode")
    nace = (raw.get("naeringskode1") or {}).get("kode")
    record = Registry(
        country="NO",
        id=raw["organisasjonsnummer"],
        name=raw.get("navn"),
        founded=parse_date(raw.get("stiftelsesdato")),
        form=form,
        industry_code=nace,
        industry_scheme="NACE/SN" if nace else None,
        municipality=((raw.get("forretningsadresse") or {}).get("kommune") or "").title() or None,
        website=raw.get("hjemmeside") or None,
        status=_status(raw),
        employees=raw.get("antallAnsatte"),  # stated only when the company reports staff
    )
    return private_person(record) if form == "ENK" else record


def _from_candidate_row(row: dict) -> Registry:
    """A row of the research weekly probe (new AS with blue codes or names)."""
    return Registry(
        country="NO",
        id=row["orgnr"],
        name=row.get("name"),
        founded=parse_date(row.get("founded")),
        form="AS",
        industry_code=row.get("nace") or None,
        industry_scheme="NACE/SN" if row.get("nace") else None,
        municipality=(row.get("municipality") or "").title() or None,
        website=row.get("website") or None,
    )


def newly_founded(record: Registry, registered: tuple[date, date], seen_at: datetime) -> Signal:
    payload = {
        "form": record.form,
        "industry_code": record.industry_code,
        "founded": record.founded.isoformat() if record.founded else None,
    }
    exact = registered[0] if registered[0] == registered[1] else None
    if exact is None:
        payload["registered_between"] = [registered[0].isoformat(), registered[1].isoformat()]
    return make_signal(
        SOURCE,
        "newly_founded",
        EntityRef(registry="brreg", id=record.id, name=record.name),
        key=record.id,
        event_date=exact,
        first_seen_at=seen_at,
        url=f"https://virksomhet.brreg.no/oppslag/enheter/{record.id}",
        title=f"New company: {record.name}",
        payload=payload,
    )


def _get(path: str, params: dict | None = None) -> net.CachedResponse:
    return net.get(f"{API}/{path}", params=params, offline=False, use_cache=False)


# --------------------------------------------------------------------------- new companies
def fetch_window(since: date, until: date, form: str) -> tuple[list[dict], int]:
    rows: list[dict] = []
    total = 0
    for page in range(MAX_PAGES):
        data = check(
            _get(
                "enheter",
                {
                    "fraRegistreringsdatoEnhetsregisteret": since.isoformat(),
                    "tilRegistreringsdatoEnhetsregisteret": until.isoformat(),
                    "organisasjonsform": form,
                    "size": PAGE_SIZE,
                    "page": page,
                },
            )
        ).json()
        batch = (data.get("_embedded") or {}).get("enheter") or []
        rows += batch
        total = (data.get("page") or {}).get("totalElements") or 0
        if not batch or len(rows) >= total:
            break
    return rows, total


def _live_new_companies(since: date, until: date, form: str) -> ConnectorResult:
    raw, total = fetch_window(since, until, form)
    seen_at, records, signals = now(), [], []
    for row in raw:
        record = parse_entity(row)
        registered = parse_date(row.get("registreringsdatoEnhetsregisteret"))
        if not in_window(registered, since, until):
            continue
        records.append(record)
        if not record.natural_person:
            signals.append(newly_founded(record, (registered, registered), seen_at))
    detail = f"new {form} registered {span_label(since, until)}"
    if len(raw) < total:
        detail += f"; read {len(raw)} of {total} (page limit), the rest not counted"
    status = source_status(SOURCE, "live", records=len(records), detail=detail)
    return ConnectorResult(records=records, signals=signals, status=status)


def _recorded_rows(recording: Recording) -> list[tuple[Registry, tuple[date, date]]]:
    data = seed.fixture(f"sources/{recording.path}")
    if recording.path == LIVE_DAY:
        days = [parse_date(raw.get("registreringsdatoEnhetsregisteret")) for raw in data["enheter"]]
        return [(parse_entity(raw), (day, day)) for raw, day in zip(data["enheter"], days, strict=True)]
    return [
        (_from_candidate_row(row), (parse_date(week["week"][0]), parse_date(week["week"][1])))
        for week in data["weeks"]
        for row in week["rows"]
    ]


def _recorded_new_companies(since: date, until: date) -> ConnectorResult:
    used = [r for r in RECORDINGS if r.exists() and r.overlaps(since, until)]
    if not used:
        reason = f"offline and no recorded data for {span_label(since, until)}"
        return ConnectorResult(status=unavailable(SOURCE, reason))
    found: dict[str, tuple[Registry, tuple[date, date], datetime]] = {}
    for recording in used:
        for record, registered in _recorded_rows(recording):
            if since <= registered[0] and registered[1] <= until and record.id not in found:
                found[record.id] = (record, registered, recording.recorded_at)
    records = [record for record, _, _ in found.values()]
    signals = [newly_founded(r, reg, seen) for r, reg, seen in found.values() if not r.natural_person]
    status = source_status(
        SOURCE,
        "cached",
        records=len(records),
        detail=recorded_detail(used, since, until),
        data_as_of=max(r.recorded_at for r in used),
    )
    return ConnectorResult(records=records, signals=signals, status=status)


def fetch_new_companies(since: date, until: date, *, offline: bool | None = None, form: str = "AS") -> ConnectorResult:
    """New limited companies (AS) registered in the window, as Registry records plus newly_founded signals."""
    if not go_live(offline):
        return _recorded_new_companies(since, until)
    try:
        return _live_new_companies(since, until, form)
    except Exception as exc:  # the boundary: report the failure, show recorded data if there is any
        return with_live_failure(_recorded_new_companies(since, until), exc)


# --------------------------------------------------------------------------- change stream
def changed_fields(item: dict) -> list[str]:
    """Top-level fields an update changed (includeChanges). Contact fields are left out unread."""
    paths = [str(c.get("path") or "") for c in item.get("endringer") or []]
    return sorted({p.split("/")[1] for p in paths if p.count("/")} - CONTACT_KEYS)


def _updates_result(
    items: list[dict],
    since: datetime,
    state: SourceState,
    records: list[Registry],
    *,
    note: str = "",
    data_as_of: datetime | None = None,
) -> ConnectorResult:
    counts = Counter(item.get("endringstype") or "Ukjent" for item in items)
    sites = sum(1 for item in items if "hjemmeside" in changed_fields(item))
    updates = f"{len(items)} update{'' if len(items) == 1 else 's'}"
    watched = f"{len(records)} watched organisation{'' if len(records) == 1 else 's'}"
    detail = (
        f"{updates} since {since:%d %b %H:%M} UTC: {counts['Ny']} new, {counts['Endring']} changed "
        f"({sites} set a website), {counts['Sletting'] + counts['Fjernet']} struck off or removed; "
        f"{watched} changed{note}"
    )
    status = source_status(SOURCE, state, records=len(records), detail=detail, data_as_of=data_as_of)
    return ConnectorResult(records=records, status=status)


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def fetch_update_items(since: datetime, until: datetime | None = None) -> list[dict]:
    items: list[dict] = []
    params = {"dato": _stamp(since), "size": 1000, "includeChanges": "true"}
    if until:
        params["updatedBefore"] = _stamp(until)
    for page in range(UPDATE_PAGES):
        data = check(_get("oppdateringer/enheter", params | {"page": page})).json()
        batch = (data.get("_embedded") or {}).get("oppdaterteEnheter") or []
        items += batch
        if not batch or len(items) >= ((data.get("page") or {}).get("totalElements") or 0):
            break
    return items


def fetch_updates(since: datetime, *, watch: Iterable[str] = (), offline: bool | None = None) -> ConnectorResult:
    """The change stream since a moment. Every update is counted; watched organisations that changed come back
    with their current register record. New entities carry no details in the stream (new AS come from
    fetch_new_companies), and a register change has no signal type yet."""
    since = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
    watch = set(watch)
    if go_live(offline):
        try:
            items = fetch_update_items(since)
            hits = sorted({i.get("organisasjonsnummer") for i in items} & watch)[:MAX_WATCH_LOOKUPS]
            records = [r for r in (lookup(orgnr, offline=False) for orgnr in hits) if r]
        except Exception as exc:  # the boundary
            return ConnectorResult(status=failed(SOURCE, "change stream", exc))
        return _updates_result(items, since, "live", records)
    if not (FIXTURES / LIVE_UPDATES).exists():
        return ConnectorResult(status=unavailable(SOURCE, "offline and the change stream was not recorded"))
    data = seed.fixture(f"sources/{LIVE_UPDATES}")
    items = [i for i in data["items"] if _moment(i["dato"]) >= since]
    hits = sorted({i.get("organisasjonsnummer") for i in items} & watch)
    records = [r for r in map(_recorded_index().get, hits) if r]
    window = f"{_moment(data['since']):%d %b %H:%M}–{_moment(data['until']):%H:%M} UTC"
    return _updates_result(
        items,
        since,
        "cached",
        records,
        note=f"; recorded sample of the stream, {window}",
        data_as_of=fixture_time(data["recorded_at"]),
    )


def _moment(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


# --------------------------------------------------------------------------- lookup
@lru_cache(maxsize=1)
def _recorded_index() -> dict[str, Registry]:
    index: dict[str, Registry] = {}
    for recording in RECORDINGS:
        if recording.exists():
            index.update({record.id: record for record, _ in _recorded_rows(recording)})
    if (FIXTURES / LIVE_LOOKUP).exists():
        record = parse_entity(seed.fixture(f"sources/{LIVE_LOOKUP}")["response"])
        index[record.id] = record
    return index


def lookup_result(orgnr: str, *, offline: bool | None = None) -> ConnectorResult:
    """Look one entity up by organisation number; the status says whether the answer is live or recorded."""
    orgnr = re.sub(r"\s", "", orgnr)
    if not ORGNR.match(orgnr):
        return ConnectorResult(status=unavailable(SOURCE, "not a Norwegian organisation number (9 digits)"))
    if go_live(offline, lookup=True):
        try:
            resp = _get(f"enheter/{orgnr}")
            if resp.status == 404:
                return ConnectorResult(
                    status=source_status(SOURCE, "live", records=0, detail="no entity with this number in the register")
                )
            if resp.status == 410:
                record = Registry(country="NO", id=orgnr, status="deleted")
            else:
                record = parse_entity(check(resp).json())
        except Exception as exc:  # the boundary: a failed lookup is reported, never shown as "not found"
            return ConnectorResult(status=failed(SOURCE, "lookup", exc))
        return ConnectorResult(
            records=[record], status=source_status(SOURCE, "live", records=1, detail="looked up live")
        )
    record = _recorded_index().get(orgnr)
    if record is None:
        return ConnectorResult(
            status=unavailable(SOURCE, "live lookups are off and this number is not in the recorded data")
        )
    return ConnectorResult(
        records=[record],
        status=source_status(
            SOURCE, "cached", records=1, detail="live lookups are off; recorded data from 17 Oct 2026"
        ),
    )


def lookup(orgnr: str, *, offline: bool | None = None) -> Registry | None:
    found = lookup_result(orgnr, offline=offline).records
    return found[0] if found else None


# --------------------------------------------------------------------------- name search
def search_result(name: str, *, offline: bool | None = None) -> ConnectorResult:
    """Entities whose name resembles the typed name; ENK (sole traders) come back without details. The live call
    skips every cache: the typed name and the contact fields in the answer are never stored."""
    if go_live(offline, lookup=True):
        try:
            params = {"navn": name, "size": SEARCH_SIZE, "organisasjonsform": SEARCH_FORMS}
            data = check(
                net.get(f"{API}/enheter", params=params, offline=False, use_cache=False, timeout_s=SEARCH_TIMEOUT_S)
            ).json()
            records = [parse_entity(e) for e in (data.get("_embedded") or {}).get("enheter") or []]
        except Exception as exc:  # the boundary: a failed search is reported, never shown as "no match"
            return ConnectorResult(status=failed(SOURCE, "name search", exc))
        return ConnectorResult(
            records=records, status=source_status(SOURCE, "live", records=len(records), detail="searched live")
        )
    records = [r for r in _recorded_index().values() if name_rank(name, r.name) is not None]
    return ConnectorResult(
        records=records,
        status=source_status(
            SOURCE,
            "cached",
            records=len(records),
            detail="live lookups are off; searched the recorded data from 17 Oct 2026",
        ),
    )
