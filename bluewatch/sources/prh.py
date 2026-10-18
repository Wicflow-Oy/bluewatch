"""Finland: PRH open data (YTJ companies v3 and registered notices v3), keyless.

New companies are found by the business-ID registration date, because the plain registration-date
filter matches a company's latest event, not its founding.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from functools import lru_cache

from bluewatch import net, seed
from bluewatch.config import settings
from bluewatch.models import ConnectorResult, EntityRef, Registry, Signal
from bluewatch.sources.common import (
    FIXTURES,
    SEARCH_TIMEOUT_S,
    NamedRecord,
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

SOURCE = "prh"
YTJ = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies"
NOTICES = "https://avoindata.prh.fi/opendata-registerednotices-api/v3"
MAX_PAGES = 30  # 100 companies a page; a busy week has about 450 new limited companies
FORMS = {"16": "OY", "17": "OYJ"}
# Open company situations; anything else keeps PRH's own code.
SITUATIONS = {"KONK": "bankrupt", "SELTILA": "in liquidation", "SANE": "in restructuring"}
CEASED = "4"  # tradeRegisterStatus of a company struck off the trade register
SOLE_TRADER_WORDS = ("elinkeinonharjoittaja", "näringsidkare", "sole trader", "private trader")
SHARE_ISSUE_CODES = {"ANTIP", "KOROI"}  # share issue; increase of share capital
LAG_DAYS = 4  # on 17 Oct PRH listed 1 company for 16 Oct and 88 for 13 Oct
LIVE_DAY = "live_2026-10-17/prh_companies_2026-10-13.json"
LIVE_LOOKUP = "live_2026-10-17/prh_lookup_3101791-3.json"

RECORDINGS = [
    Recording(
        LIVE_DAY,
        date(2026, 10, 13),
        date(2026, 10, 13),
        True,
        fixture_time("2026-10-17T20:34:00+03:00"),
        "all limited companies registered",
    ),
    Recording(
        "weekly_scan_2026-10-05.json",
        date(2026, 10, 5),
        date(2026, 10, 11),
        False,
        fixture_time("2026-10-17T00:32:09+03:00"),
        "a weekly sample of limited companies registered",
    ),
    Recording(
        "monday10_candidates_2026-10-12.json",
        date(2026, 8, 17),
        date(2026, 10, 11),
        False,
        fixture_time("2026-10-17T00:42:49+03:00"),
        "blue and tech candidates registered",
    ),
]


# --------------------------------------------------------------------------- parsing
def _english(descriptions: list[dict] | None) -> str | None:
    by_lang = {d.get("languageCode"): d.get("description") for d in descriptions or []}
    return by_lang.get("3") or by_lang.get("1")


def _current(items: list[dict] | None) -> dict:
    return next((i for i in items or [] if not i.get("endDate")), (items or [{}])[0])


@lru_cache(maxsize=1)
def _municipalities() -> dict[str, str]:
    return seed.fixture("sources/fi_municipalities_2026.json")["codes"]


def _municipality(addresses: list[dict] | None) -> str | None:
    """The postal city can be a district, so the municipality code decides (W9)."""
    for address in sorted(addresses or [], key=lambda a: a.get("type") != 1):
        for office in address.get("postOffices") or []:
            code = office.get("municipalityCode")
            if code in _municipalities():
                return _municipalities()[code]
    return None


def _status(raw: dict) -> str | None:
    """ "ceased" once the company has an end date or left the trade register, else its open situations
    (bankrupt, in liquidation, ...), else "registered" when it is in the trade register."""
    if raw.get("endDate") or raw.get("tradeRegisterStatus") == CEASED:
        return "ceased"
    situations = [
        SITUATIONS.get(s.get("type"), s.get("type")) for s in raw.get("companySituations") or [] if not s.get("endDate")
    ]
    return ", ".join(situations) or ("registered" if raw.get("tradeRegisterStatus") == "1" else None)


def parse_company(raw: dict) -> Registry:
    """One company from a YTJ v3 response. A missing TOL code stays None (often 2-6 weeks after founding)."""
    form = _current(raw.get("companyForms"))
    names = [n for n in raw.get("names") or [] if n.get("type") == "1"] or raw.get("names") or [{}]
    line = raw.get("mainBusinessLine") or {}
    code = (line.get("type") or "").strip()
    website = raw.get("website")
    record = Registry(
        country="FI",
        id=raw["businessId"]["value"],
        name=_current(names).get("name"),
        founded=parse_date(raw["businessId"].get("registrationDate")),
        form=FORMS.get(form.get("type"), _english(form.get("descriptions"))),
        industry_code=code if code.strip("0") else None,
        industry_scheme=f"TOL/{line.get('typeCodeSet')}" if code.strip("0") else None,
        municipality=_municipality(raw.get("addresses")),
        website=(website.get("url") if isinstance(website, dict) else website) or None,
        status=_status(raw),
    )
    descriptions = " ".join(d.get("description", "").lower() for d in form.get("descriptions") or [])
    return private_person(record) if any(w in descriptions for w in SOLE_TRADER_WORDS) else record


def parse_search_hit(raw: dict) -> Registry:
    """A company from a name search, with its other names: a name that ended before the company did is a former
    name (Aker Arctic Technology Oy, now Railo Technology Oy); parallel and auxiliary names still in use are kept."""
    record = parse_company(raw)
    if record.natural_person:
        return record
    names = [n for n in raw.get("names") or [] if n.get("name") and n["name"] != record.name]
    former = [n["name"] for n in names if n.get("endDate") and n["endDate"] != raw.get("endDate")]
    other = [n["name"] for n in names if n["name"] not in former]
    return NamedRecord(**record.model_dump(), former_names=former, other_names=other)


def _from_scan_row(row: dict) -> Registry:
    """A row of the research weekly scan or the Monday candidates (limited companies only)."""
    return Registry(
        country="FI",
        id=row["id"],
        name=row.get("name"),
        founded=parse_date(row.get("founded")),
        form="OY",
        industry_code=row.get("tol") or None,
        industry_scheme="TOL" if row.get("tol") else None,
        website=row.get("website_field") or None,
    )


def _from_probe_row(row: dict) -> Registry:
    return Registry(
        country="FI",
        id=row["businessId"],
        name=row.get("name"),
        founded=parse_date(row.get("idDate")),
        form="OY" if row.get("form") == "Limited company" else row.get("form"),
        industry_code=row.get("tol") or None,
        industry_scheme=f"TOL/{row['tolSet']}" if row.get("tolSet") else None,
        website=row.get("website") or None,
    )


def newly_founded(record: Registry, seen_at: datetime, *, window: tuple[date, date] | None = None) -> Signal:
    payload = {"form": record.form, "industry_code": record.industry_code}
    if record.founded is None and window:
        payload["registered_between"] = [window[0].isoformat(), window[1].isoformat()]
    return make_signal(
        SOURCE,
        "newly_founded",
        EntityRef(registry="prh", id=record.id, name=record.name),
        key=record.id,
        event_date=record.founded,
        first_seen_at=seen_at,
        url=f"https://tietopalvelu.ytj.fi/yritys/{record.id}",
        title=f"New company: {record.name}",
        payload=payload,
    )


def _result(records: list[Registry], seen_at: datetime, status) -> ConnectorResult:
    signals = [newly_founded(r, seen_at) for r in records if not r.natural_person]
    return ConnectorResult(records=records, signals=signals, status=status)


# --------------------------------------------------------------------------- new companies
def fetch_window(since: date, until: date) -> tuple[list[dict], int]:
    found: dict[str, dict] = {}
    total = 0
    for page in range(1, MAX_PAGES + 1):
        params = {
            "businessIdRegistrationStart": since.isoformat(),
            "businessIdRegistrationEnd": until.isoformat(),
            "companyForm": "OY",
        }
        if page > 1:
            params["page"] = page
        data = check(net.get(YTJ, params=params, offline=False)).json()
        total = data.get("totalResults") or 0
        before = len(found)
        found.update({c["businessId"]["value"]: c for c in data.get("companies") or []})
        if len(found) == before or len(found) >= total:
            break
    return list(found.values()), total


def _live_new_companies(since: date, until: date) -> ConnectorResult:
    raw, total = fetch_window(since, until)
    records = [r for r in map(parse_company, raw) if in_window(r.founded, since, until)]
    detail = f"limited companies registered {span_label(since, until)}"
    if len(raw) < total:
        detail += f"; read {len(raw)} of {total} (page limit), the rest not counted"
    if until > settings().today - timedelta(days=LAG_DAYS):
        detail += "; PRH lists new companies a few days late, so the latest days are still filling in"
    return _result(records, now(), source_status(SOURCE, "live", records=len(records), detail=detail))


def _recorded_rows(recording: Recording) -> list[Registry]:
    data = seed.fixture(f"sources/{recording.path}")
    if recording.path == LIVE_DAY:
        return [parse_company(c) for c in data["companies"]]
    if "A_newly_founded" in data:
        return [_from_scan_row(r) for r in data["A_newly_founded"]["probed"]]
    return [_from_scan_row(r) for r in data["results"]]


def _recorded_new_companies(since: date, until: date) -> ConnectorResult:
    used = [r for r in RECORDINGS if r.exists() and r.overlaps(since, until)]
    if not used:
        reason = f"offline and no recorded data for {span_label(since, until)}"
        return ConnectorResult(status=unavailable(SOURCE, reason))
    merged: dict[str, Registry] = {}
    first_seen: dict[str, tuple[datetime, tuple[date, date]]] = {}  # earliest recording and the window it covers
    for recording in sorted(used, key=lambda r: r.recorded_at):
        for row in _recorded_rows(recording):
            if row.id in merged:  # a later recording may fill a gap, such as the founding date
                gaps = {k: v for k, v in row if v and not getattr(merged[row.id], k)}
                merged[row.id] = merged[row.id].model_copy(update=gaps)
            else:
                merged[row.id] = row
                first_seen[row.id] = (recording.recorded_at, (recording.start, recording.end))
    records, signals = [], []
    for record in merged.values():
        seen_at, recorded_window = first_seen[record.id]
        window = (record.founded, record.founded) if record.founded else recorded_window
        if since <= window[0] and window[1] <= until:
            records.append(record)
            if not record.natural_person:
                signals.append(newly_founded(record, seen_at, window=window))
    status = source_status(
        SOURCE,
        "cached",
        records=len(records),
        detail=recorded_detail(used, since, until),
        data_as_of=max(r.recorded_at for r in used),
    )
    return ConnectorResult(records=records, signals=signals, status=status)


def fetch_new_companies(since: date, until: date, *, offline: bool | None = None) -> ConnectorResult:
    """Limited companies registered in the window, as Registry records plus newly_founded signals."""
    if not go_live(offline):
        return _recorded_new_companies(since, until)
    try:
        return _live_new_companies(since, until)
    except Exception as exc:  # the boundary: report the failure, show recorded data if there is any
        return with_live_failure(_recorded_new_companies(since, until), exc)


# --------------------------------------------------------------------------- lookup
def normalise_business_id(text: str) -> str | None:
    """'FI31017913', '31017913' and '3101791-3' are the same ID. The checksum is the resolver's job."""
    digits = re.sub(r"[\s-]", "", text.upper()).removeprefix("FI")
    return f"{digits[:7]}-{digits[7]}" if re.fullmatch(r"\d{8}", digits) else None


@lru_cache(maxsize=1)
def _recorded_index() -> dict[str, Registry]:
    """Every Finnish company in the recorded files, for offline lookups."""
    index: dict[str, Registry] = {}
    probe = seed.fixture("sources/prh_blue_probe.json")
    for group in list(probe["by_name"].values()) + list(probe["by_tol"].values()):
        index.update({r.id: r for r in map(_from_probe_row, group["sample"])})
    for recording in RECORDINGS:
        if recording.exists():
            index.update({r.id: r for r in _recorded_rows(recording)})
    raw = seed.fixture("sources/krek_antip_oct2026.json")["companies"]
    if (FIXTURES / LIVE_LOOKUP).exists():
        raw = raw + seed.fixture(f"sources/{LIVE_LOOKUP}")["response"]["companies"]
    index.update({r.id: r for r in map(parse_company, raw)})
    return index


def lookup_result(business_id: str, *, offline: bool | None = None) -> ConnectorResult:
    """Look one company up by business ID; the status says whether the answer is live or recorded."""
    business_id = normalise_business_id(business_id)
    if business_id is None:
        return ConnectorResult(status=unavailable(SOURCE, "not a Finnish business ID (1234567-8)"))
    if go_live(offline, lookup=True):
        try:
            data = check(net.get(YTJ, params={"businessId": business_id}, offline=False, use_cache=False)).json()
        except Exception as exc:  # the boundary: a failed lookup is reported, never shown as "not found"
            return ConnectorResult(status=failed(SOURCE, "lookup", exc))
        records = [parse_company(c) for c in data.get("companies") or []][:1]
        detail = "looked up live" if records else "PRH open data has no company with this business ID"
        return ConnectorResult(
            records=records, status=source_status(SOURCE, "live", records=len(records), detail=detail)
        )
    record = _recorded_index().get(business_id)
    if record is None:
        return ConnectorResult(
            status=unavailable(SOURCE, "live lookups are off and this ID is not in the recorded data")
        )
    return ConnectorResult(
        records=[record],
        status=source_status(
            SOURCE, "cached", records=1, detail="live lookups are off; recorded data from 16-17 Oct 2026"
        ),
    )


def lookup(business_id: str, *, offline: bool | None = None) -> Registry | None:
    found = lookup_result(business_id, offline=offline).records
    return found[0] if found else None


# --------------------------------------------------------------------------- name search
def search_result(name: str, *, offline: bool | None = None) -> ConnectorResult:
    """Companies the register finds by name, sole traders without details. The live call skips every cache, so the
    typed name is never written anywhere."""
    if go_live(offline, lookup=True):
        try:
            data = check(
                net.get(YTJ, params={"name": name}, offline=False, use_cache=False, timeout_s=SEARCH_TIMEOUT_S)
            ).json()
            records = [parse_search_hit(c) for c in data.get("companies") or []]
        except Exception as exc:  # the boundary: a failed search is reported, never shown as "no match"
            return ConnectorResult(status=failed(SOURCE, "name search", exc))
        total = data.get("totalResults") or len(records)
        detail = "searched live"
        if total > len(records):
            detail += f"; read the first {len(records)} of {total} names"
        return ConnectorResult(
            records=records, status=source_status(SOURCE, "live", records=len(records), detail=detail)
        )
    records = [r for r in _recorded_index().values() if name_rank(name, r.name) is not None]
    return ConnectorResult(
        records=records,
        status=source_status(
            SOURCE,
            "cached",
            records=len(records),
            detail="live lookups are off; searched the recorded data from 16-17 Oct 2026",
        ),
    )


# --------------------------------------------------------------------------- share issues
def _share_issue_signals(business_id: str, notices: list[dict], seen_at: datetime) -> list[Signal]:
    """One signal per distinct filing date that carries a share-issue entry code."""
    by_day: dict[date, set[str]] = {}
    for notice in notices:
        codes = {c for c in notice.get("entryCodes") or notice.get("codes") or [] if c}
        day = parse_date(notice.get("registrationDate") or notice.get("date"))
        if day and codes & SHARE_ISSUE_CODES:
            by_day.setdefault(day, set()).update(codes)
    return [
        make_signal(
            SOURCE,
            "share_issue",
            EntityRef(registry="prh", id=business_id),
            key=f"{business_id}:{day}",
            event_date=day,
            first_seen_at=seen_at,
            url=f"https://tietopalvelu.ytj.fi/yritys/{business_id}",
            title="Share issue registered",
            payload={"entry_codes": sorted(codes)},
        )
        for day, codes in sorted(by_day.items())
    ]


def recorded_share_issues() -> list[Signal]:
    """All share issues in the recorded notices (October 2026 sample and the demo companies' histories)."""
    signals = []
    for company in seed.fixture("sources/krek_antip_oct2026.json")["companies"]:
        signals += _share_issue_signals(
            company["businessId"]["value"],
            company.get("publicNotices") or [],
            fixture_time("2026-10-16T22:36:16+03:00"),
        )
    for company in seed.load("signals_cache")["companies"]:
        notices = (company.get("prh_notices") or {}).get("val") or []
        if company.get("fi_business_id") and notices:
            signals += _share_issue_signals(
                company["fi_business_id"], notices, fixture_time("2026-10-17T00:51:00+03:00")
            )
    return list({s.id: s for s in signals}.values())


def share_issues_result(business_id: str, *, offline: bool | None = None) -> ConnectorResult:
    business_id = normalise_business_id(business_id)
    if business_id is None:
        return ConnectorResult(status=unavailable(SOURCE, "not a Finnish business ID (1234567-8)"))
    if go_live(offline, lookup=True):
        try:
            data = check(net.get(f"{NOTICES}/{business_id}", offline=False, use_cache=False)).json()
        except Exception as exc:  # the boundary
            return ConnectorResult(status=failed(SOURCE, "registered notices", exc))
        companies = data.get("companies") if isinstance(data, dict) and "companies" in data else [data]
        notices = [n for c in companies for n in c.get("publicNotices") or []]
        signals = _share_issue_signals(business_id, notices, now())
        return ConnectorResult(
            signals=signals,
            status=source_status(
                SOURCE, "live", records=len(signals), detail=f"{len(notices)} registered notices read"
            ),
        )
    recorded = [s for s in recorded_share_issues() if s.entity_ref.id == business_id]
    known = business_id in {c.get("fi_business_id") for c in seed.load("signals_cache")["companies"]}
    if not recorded and not known:
        return ConnectorResult(status=unavailable(SOURCE, "this company's notices were not recorded"))
    return ConnectorResult(
        signals=recorded,
        status=source_status(
            SOURCE, "cached", records=len(recorded), detail="recorded registered notices from 16-17 Oct 2026"
        ),
    )


def share_issues(business_id: str, *, offline: bool | None = None) -> list[Signal]:
    """Share-issue filings (entry codes ANTIP, KOROI), one signal per distinct date. Use share_issues_result to tell
    "none" from "not available"."""
    return share_issues_result(business_id, offline=offline).signals
