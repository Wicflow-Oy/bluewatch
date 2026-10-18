"""EU public tenders: the TED search API v3 (keyless). Open tenders by CPV and buyer country; awards by winner ID.

A CPV code in a TED query also matches its sub-codes (90733000 finds 90733100), so a prefix such as "345" is sent
as 34500000 and the same prefix rule is applied to recorded notices.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from bluewatch import net, seed
from bluewatch.config import settings
from bluewatch.models import ConnectorResult, EntityRef, Signal
from bluewatch.sources.common import (
    FIXTURES,
    NOT_ZERO,
    check,
    failed,
    fixture_time,
    go_live,
    make_signal,
    now,
    parse_date,
    source_status,
    unavailable,
    with_live_failure,
)

SOURCE = "ted"
SEARCH = "https://api.ted.europa.eu/v3/notices/search"
BLUE_CPV = (
    "34500000 34510000 34512000 34520000 34521000 34930000 35513000 38221000 38290000 38420000 "
    "63720000 71354000 73112000 90733000 09230000"
).split()
NORDIC_BALTIC = ["FI", "SE", "NO", "DK", "EE", "LV", "LT"]
ALPHA3 = {
    "FI": "FIN",
    "SE": "SWE",
    "NO": "NOR",
    "DK": "DNK",
    "EE": "EST",
    "LV": "LVA",
    "LT": "LTU",
    "IS": "ISL",
    "DE": "DEU",
    "PL": "POL",
}
ALPHA2 = {v: k for k, v in ALPHA3.items()}
TENDER_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-type",
    "buyer-name",
    "buyer-country",
    "notice-title",
    "deadline-receipt-tender-date-lot",
    "classification-cpv",
]
AWARD_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-type",
    "buyer-name",
    "buyer-country",
    "notice-title",
    "classification-cpv",
    "winner-name",
    "winner-identifier",
    "result-value-notice",
]
LOOKBACK_DAYS = 120  # contract notices stay open for weeks; older ones have closed
PAGE_LIMIT = 100
MAX_PAGES = 5
RECORDED_OPEN = "ted_open_tenders_blue_nordic_baltic.json"
LIVE_OPEN = "live_2026-10-17/ted_open_tenders_2026-10-17.json"
LIVE_AWARDS = "live_2026-10-17/ted_awards_3101791-3.json"


# --------------------------------------------------------------------------- notices
def _texts(value) -> list[str]:
    """TED fields are per language ({"eng": "..."} or {"fin": ["...", "..."]}); prefer English."""
    if isinstance(value, dict):
        value = value.get("eng") or next(iter(value.values()), [])
    return list(dict.fromkeys(value if isinstance(value, list) else [value] if value else []))


def _first_text(value) -> str | None:
    return next(iter(_texts(value)), None)


def _notice(raw: dict) -> dict:
    """The fields we use from one search hit, in plain form."""
    deadlines = raw.get("deadline-receipt-tender-date-lot") or []
    deadlines = deadlines if isinstance(deadlines, list) else [deadlines]
    return {
        "pub": raw.get("publication-number"),
        "published": parse_date(raw.get("publication-date")),
        "type": raw.get("notice-type"),
        "title": _first_text(raw.get("notice-title")),
        "buyer": _first_text(raw.get("buyer-name")),
        "countries": sorted({ALPHA2.get(c, c) for c in raw.get("buyer-country") or []}),
        "deadlines": sorted({d.isoformat() for d in map(parse_date, deadlines) if d}),
        "cpv": sorted(set(raw.get("classification-cpv") or [])),
    }


def _recorded_row(row: dict) -> dict:
    """A row of the recorded open-tender file (one TED query; relevance tagged by a human reading titles)."""
    return {
        "pub": row["pub"],
        "published": parse_date(row.get("date")),
        "type": None,
        "title": row.get("title"),
        "buyer": row.get("buyer"),
        "countries": sorted(ALPHA2.get(c, c) for c in row.get("country") or []),
        "deadlines": row.get("deadlines") or [],
        "cpv": row.get("cpv") or [],
        "relevance": row.get("relevance"),
        "relevance_note": row.get("relevance_note"),
    }


def _url(pub: str) -> str:
    return f"https://ted.europa.eu/en/notice/-/detail/{pub}"


def open_tender_signal(notice: dict, seen_at: datetime, today: date) -> Signal:
    upcoming = [d for d in notice["deadlines"] if d >= today.isoformat()]
    if upcoming:
        deadline = upcoming[0]
    else:
        deadline = notice["deadlines"][-1] if notice["deadlines"] else None
    payload = {
        "deadline": deadline,
        "deadlines": notice["deadlines"],
        "cpv": notice["cpv"],
        "buyer": notice["buyer"],
        "buyer_country": notice["countries"],
        "publication_number": notice["pub"],
        "notice_type": notice["type"],
    }
    payload |= {k: notice[k] for k in ("relevance", "relevance_note") if notice.get(k)}
    return make_signal(
        SOURCE,
        "open_tender",
        EntityRef(name=notice["buyer"]),
        key=notice["pub"],
        event_date=notice["published"],
        first_seen_at=seen_at,
        url=_url(notice["pub"]),
        title=notice["title"],
        payload=payload,
    )


def search(query: str, fields: list[str], scope: str) -> list[dict]:
    notices: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        body = {"query": query, "fields": fields, "limit": PAGE_LIMIT, "page": page, "scope": scope}
        batch = check(net.post(SEARCH, body, offline=False)).json().get("notices") or []
        notices += batch
        if len(batch) < PAGE_LIMIT:
            break
    return notices


def open_tender_query(cpv: list[str], countries: list[str], since: date) -> str:
    return (
        f"notice-type IN (cn-standard cn-social cn-desg) "
        f"AND buyer-country IN ({' '.join(ALPHA3.get(c, c) for c in countries)}) "
        f"AND classification-cpv IN ({' '.join(c.ljust(8, '0') for c in cpv)}) "
        f"AND publication-date>={since:%Y%m%d}"
    )


# --------------------------------------------------------------------------- open tenders
def _cpv_match(code: str, prefixes: list[str]) -> bool:
    return code.startswith(tuple(p.rstrip("0") or p for p in prefixes))


def _keep(notice: dict, cpv_prefixes: list[str], countries: list[str], today: date) -> bool:
    return (
        bool(notice["deadlines"])
        and max(notice["deadlines"]) >= today.isoformat()
        and any(_cpv_match(c, cpv_prefixes) for c in notice["cpv"])
        and bool(set(notice["countries"]) & set(countries))
    )


def _recorded_open(cpv_prefixes: list[str], countries: list[str], today: date) -> ConnectorResult:
    research = seed.fixture(f"sources/{RECORDED_OPEN}")
    tags = {row["pub"]: _recorded_row(row) for row in research["open"] + research["no_deadline"]}
    if (FIXTURES / LIVE_OPEN).exists():
        live = seed.fixture(f"sources/{LIVE_OPEN}")
        notices = {n["pub"]: n for n in map(_notice, live["notices"])}
        for pub, row in tags.items():
            if pub in notices:
                notices[pub] |= {k: row[k] for k in ("relevance", "relevance_note")}
        recorded_at = fixture_time(live["recorded_at"])
    else:
        notices, recorded_at = tags, fixture_time("2026-10-17T01:16:46+03:00")
    kept = [n for n in notices.values() if _keep(n, cpv_prefixes, countries, today)]
    detail = f"recorded {recorded_at:%d %b %Y}: {len(kept)} open with a deadline on or after {today:%d %b}"
    # Both recordings asked for BLUE_CPV and NORDIC_BALTIC; anything else was never asked for.
    other_codes = [p for p in cpv_prefixes if not any(_cpv_match(c, [p]) or _cpv_match(p, [c]) for c in BLUE_CPV)]
    if other_codes or set(countries) - set(NORDIC_BALTIC):
        detail += f"; the recording did not cover every code or country asked ({NOT_ZERO})"
    signals = [open_tender_signal(n, recorded_at, today) for n in kept]
    return ConnectorResult(
        signals=signals,
        status=source_status(SOURCE, "cached", records=len(signals), detail=detail, data_as_of=recorded_at),
    )


def open_tenders(
    cpv_prefixes: list[str] = BLUE_CPV,
    countries: list[str] = NORDIC_BALTIC,
    *,
    today: date | None = None,
    offline: bool | None = None,
) -> ConnectorResult:
    """Contract notices still open (a deadline today or later); deadline, CPV codes and buyer are in the payload."""
    today = today or settings().today
    if not go_live(offline):
        return _recorded_open(cpv_prefixes, countries, today)
    try:
        query = open_tender_query(cpv_prefixes, countries, today - timedelta(days=LOOKBACK_DAYS))
        notices = [_notice(raw) for raw in search(query, TENDER_FIELDS, "ACTIVE")]
    except Exception as exc:  # the boundary: report the failure, show recorded data
        return with_live_failure(_recorded_open(cpv_prefixes, countries, today), exc)
    seen_at = now()
    signals = [open_tender_signal(n, seen_at, today) for n in notices if _keep(n, cpv_prefixes, countries, today)]
    detail = f"{len(signals)} open with a deadline on or after {today:%d %b} ({len(notices)} active notices read)"
    return ConnectorResult(signals=signals, status=source_status(SOURCE, "live", records=len(signals), detail=detail))


# --------------------------------------------------------------------------- awards
def id_variants(business_id: str, country: str) -> list[str]:
    """Buyers type the winner's ID in different shapes: 3101791-3, 31017913, FI31017913."""
    bare = re.sub(r"[\s-]", "", business_id.upper()).removeprefix(country.upper())
    if country.upper() == "FI" and re.fullmatch(r"\d{8}", bare):
        return [f"{bare[:7]}-{bare[7]}", bare, f"FI{bare}"]
    if country.upper() == "NO" and re.fullmatch(r"\d{9}", bare):
        return [bare, f"NO{bare}MVA"]
    return [bare]


def award_signal(raw: dict, winner_id: str, country: str, seen_at: datetime) -> Signal:
    notice = _notice(raw)
    ids = raw.get("winner-identifier") or []
    names = _texts(raw.get("winner-name"))
    value = raw.get("result-value-notice")
    payload = {
        "winner_id": winner_id,
        "winner_name": names[0] if len(ids) == 1 and names else None,
        "co_winners": max(len(ids) - 1, 0),
        "buyer": notice["buyer"],
        "buyer_country": notice["countries"],
        "cpv": notice["cpv"],
        "publication_number": notice["pub"],
        "notice_type": notice["type"],
        "result_value": float(value) if isinstance(value, str) and re.fullmatch(r"[\d.]+", value) else None,
    }
    registry = {"FI": "prh", "NO": "brreg", "EE": "rik"}.get(country.upper())
    return make_signal(
        SOURCE,
        "award",
        EntityRef(registry=registry, id=winner_id, name=payload["winner_name"]),
        key=f"{notice['pub']}:{winner_id}",
        event_date=notice["published"],
        first_seen_at=seen_at,
        url=_url(notice["pub"]),
        title=notice["title"],
        payload=payload,
    )


def _cached_award(row: dict, winner_id: str, country: str) -> dict:
    """An award from the demo signals cache (publication number, date, buyer and title only)."""
    return {
        "publication-number": row["pub"],
        "publication-date": row.get("date"),
        "buyer-name": {"und": [row.get("buyer")]},
        "notice-title": {"eng": row.get("title")},
        "winner-identifier": [winner_id],
    }


def _recorded_awards(winner_id: str, country: str) -> ConnectorResult:
    variants = set(id_variants(winner_id, country))
    found: dict[str, tuple[dict, datetime]] = {}
    for company in seed.load("signals_cache")["companies"]:
        if variants & {company.get("fi_business_id"), company.get("no_orgnr")}:
            for row in ((company.get("ted") or {}).get("val") or {}).get("notices") or []:
                found[row["pub"]] = (_cached_award(row, winner_id, country), fixture_time("2026-10-17T00:51:00+03:00"))
    probe = seed.fixture("sources/ted_fi_awards_probe.json")["notices"]
    found |= {
        n["publication-number"]: (n, fixture_time("2026-10-16T22:49:13+03:00"))
        for n in probe
        if variants & set(n.get("winner-identifier") or [])
    }
    if (FIXTURES / LIVE_AWARDS).exists():
        live = seed.fixture(f"sources/{LIVE_AWARDS}")
        if variants & set(live["winner_ids"]):
            found |= {n["publication-number"]: (n, fixture_time(live["recorded_at"])) for n in live["notices"]}
    if not found:
        return ConnectorResult(status=unavailable(SOURCE, "this winner's awards were not recorded"))
    signals = [award_signal(raw, winner_id, country, seen) for raw, seen in found.values()]
    return ConnectorResult(
        signals=signals,
        status=source_status(
            SOURCE, "cached", records=len(signals), detail=f"recorded award notices naming this winner: {len(signals)}"
        ),
    )


def awards_result(business_id: str, country: str, *, offline: bool | None = None) -> ConnectorResult:
    winner_id = id_variants(business_id, country)[0]
    if not go_live(offline, lookup=True):
        return _recorded_awards(winner_id, country)
    try:
        query = f"winner-identifier IN ({' '.join(id_variants(business_id, country))})"
        notices = search(query, AWARD_FIELDS, "ALL")
    except Exception as exc:  # the boundary
        return ConnectorResult(status=failed(SOURCE, "award search", exc))
    seen_at = now()
    signals = [award_signal(raw, winner_id, country, seen_at) for raw in notices]
    return ConnectorResult(
        signals=signals,
        status=source_status(
            SOURCE, "live", records=len(signals), detail=f"award notices naming this winner: {len(signals)}"
        ),
    )


def awards_by_winner(business_id: str, country: str, *, offline: bool | None = None) -> list[Signal]:
    """Award notices that name the company as a winner (type "award"; the winner's ID is in the payload).
    Use awards_result to tell "no awards" from "not available"."""
    return awards_result(business_id, country, offline=offline).signals


def recorded_notices() -> list[Signal]:
    """Every recorded notice with its real dates, for replays: tenders (open or closed now) and awards."""
    research = seed.fixture(f"sources/{RECORDED_OPEN}")
    seen_at = fixture_time("2026-10-17T01:16:46+03:00")
    signals = [
        open_tender_signal(_recorded_row(r), seen_at, settings().today)
        for r in research["open"] + research["no_deadline"]
    ]
    for company in seed.load("signals_cache")["companies"]:
        winner = company.get("fi_business_id") or company.get("no_orgnr")
        if winner:
            signals += _recorded_awards(winner, "FI" if company.get("fi_business_id") else "NO").signals
    return list({s.id: s for s in signals}.values())
