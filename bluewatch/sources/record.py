"""Record the fixtures the offline app and the tests use. Run by hand, never in tests.

    python -m bluewatch.sources.record estonia <download_dir>   # extracts from the RIK daily files, no network
    python -m bluewatch.sources.record live [prh brreg ted rik search] # about 10 requests, 1 per second, generic UA

Nothing is stored that the app must not keep: no contact fields, no sole traders' details and no street
addresses. A register address is kept to its municipality: a new company is often registered at a founder's
home, and a c/o line can name a person.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from bluewatch import net
from bluewatch.sources import brreg, prh, rik, ted
from bluewatch.sources.common import CONTACT_KEYS, FIXTURES, check, drop_contacts, now

EE_WINDOW = (date(2026, 8, 22), date(2026, 10, 16))
PRH_DAY = date(2026, 10, 13)
BRREG_DAY = date(2026, 10, 16)


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def write_table(path: Path, header: dict, columns: list[str], rows: list[list]) -> None:
    """A header plus one compact row per line: small, and still readable in a diff."""
    body = ",\n".join("  " + json.dumps(row, ensure_ascii=False) for row in rows)
    head = json.dumps(header | {"columns": columns}, ensure_ascii=False, indent=1)[:-2]
    path.write_text(f'{head},\n "rows": [\n{body}\n ]\n}}\n', encoding="utf-8")


def record_estonia(download_dir: Path) -> None:
    """New legal persons for the window with EMTAK codes (about 5 minutes: the general file is streamed),
    then the lookup index of all legal persons."""
    simple = download_dir / rik.SIMPLE_CSV
    result = rik.load_new_companies(*EE_WINDOW, simple_csv_zip=simple, general_json_zip=download_dir / rik.GENERAL_JSON)
    if result.status.state == "unavailable":
        raise SystemExit(result.status.detail)
    header = {
        "source": f"{rik.FILES_URL}{rik.SIMPLE_CSV} and {rik.GENERAL_JSON} (CC BY 4.0)",
        "file_date": f"{result.status.data_as_of:%d %b %Y}",
        "since": EE_WINDOW[0].isoformat(),
        "until": EE_WINDOW[1].isoformat(),
        "recorded_at": now().isoformat(timespec="seconds"),
        "detail": result.status.detail,
    }
    rows = [[r.model_dump(mode="json")[c] for c in rik.RECORDED_COLUMNS] for r in result.records]
    write_table(FIXTURES / rik.RECORDED, header, rik.RECORDED_COLUMNS, rows)
    print(result.status.detail)
    print(f"index: {rik.build_index(simple, FIXTURES / rik.INDEX)} legal persons")


BRREG_FIELDS = (
    "organisasjonsnummer",
    "navn",
    "organisasjonsform",
    "naeringskode1",
    "stiftelsesdato",
    "registreringsdatoEnhetsregisteret",
    "hjemmeside",
    "konkurs",
    "underAvvikling",
    "underTvangsavviklingEllerTvangsopplosning",
    "slettedato",
)


def slim_entity(entity: dict) -> dict:
    """The fields the connector reads; the address is kept to its municipality."""
    slim = {k: entity[k] for k in BRREG_FIELDS if k in entity}
    address = entity.get("forretningsadresse") or {}
    slim["forretningsadresse"] = {k: address[k] for k in ("kommune", "kommunenummer", "landkode") if k in address}
    return slim


def slim_notice(notice: dict) -> dict:
    """Drop the per-language link lists and keep English titles, which is all the connector reads."""
    return {
        k: ({"eng": v["eng"]} if isinstance(v, dict) and "eng" in v else v) for k, v in notice.items() if k != "links"
    }


def private_update(item: dict, known: set[str]) -> dict:
    """Keep the change type, time and changed field paths, never the values; keep the organisation number only
    for known limited companies, since any other update may be a sole trader's."""
    kept = {k: item[k] for k in ("oppdateringsid", "dato", "endringstype") if k in item}
    kept["endringer"] = [
        {"op": c.get("op"), "path": c.get("path")}
        for c in item.get("endringer") or []
        if str(c.get("path") or "/").split("/")[1] not in CONTACT_KEYS
    ]
    if item.get("organisasjonsnummer") in known:
        kept["organisasjonsnummer"] = item["organisasjonsnummer"]
    return kept


def _stamp() -> dict:
    return {"recorded_at": now().isoformat(timespec="seconds")}


def municipality_only(company: dict) -> dict:
    """A PRH company with each address kept to its type and municipality code, all the connector reads."""
    addresses = [
        {
            "type": a.get("type"),
            "postOffices": [{"municipalityCode": o.get("municipalityCode")} for o in a.get("postOffices") or []],
        }
        for a in company.get("addresses") or []
    ]
    return company | {"addresses": addresses}


def record_prh() -> None:
    """PRH lists new companies a few days late, so the sample day is 13 Oct, not the day before recording."""
    companies, total = prh.fetch_window(PRH_DAY, PRH_DAY)
    companies = [municipality_only(c) for c in drop_contacts(companies)]
    _write(
        FIXTURES / prh.LIVE_DAY,
        _stamp()
        | {"request": f"{prh.YTJ} businessIdRegistration {PRH_DAY}, OY", "totalResults": total, "companies": companies},
    )
    found = drop_contacts(check(net.get(prh.YTJ, params={"businessId": "3101791-3"}, offline=False)).json())
    found["companies"] = [municipality_only(c) for c in found.get("companies") or []]
    _write(FIXTURES / prh.LIVE_LOOKUP, _stamp() | {"businessId": "3101791-3", "response": found})


def record_brreg() -> None:
    entities, total = brreg.fetch_window(BRREG_DAY, BRREG_DAY, "AS")
    _write(
        FIXTURES / brreg.LIVE_DAY,
        _stamp()
        | {
            "request": f"{brreg.API}/enheter registered {BRREG_DAY}, AS",
            "totalElements": total,
            "enheter": list(map(slim_entity, entities)),
        },
    )
    since, until = datetime(2026, 10, 16, 6, tzinfo=timezone.utc), datetime(2026, 10, 16, 9, tzinfo=timezone.utc)
    known = {e["organisasjonsnummer"] for e in entities} | {"938525420"}
    items = [private_update(i, known) for i in brreg.fetch_update_items(since, until)]
    _write(
        FIXTURES / brreg.LIVE_UPDATES,
        _stamp() | {"since": since.isoformat(), "until": until.isoformat(), "items": items},
    )
    entity = check(net.get(f"{brreg.API}/enheter/938525420", offline=False, use_cache=False)).json()
    _write(FIXTURES / brreg.LIVE_LOOKUP, _stamp() | {"orgnr": "938525420", "response": slim_entity(entity)})


def record_ted() -> None:
    query = ted.open_tender_query(ted.BLUE_CPV, ted.NORDIC_BALTIC, BRREG_DAY - timedelta(days=ted.LOOKBACK_DAYS))
    notices = ted.search(query, ted.TENDER_FIELDS, "ACTIVE")
    _write(FIXTURES / ted.LIVE_OPEN, _stamp() | {"query": query, "notices": list(map(slim_notice, notices))})
    winner_ids = ted.id_variants("3101791-3", "FI")
    query = f"winner-identifier IN ({' '.join(winner_ids)})"
    notices = ted.search(query, ted.AWARD_FIELDS, "ALL")
    _write(
        FIXTURES / ted.LIVE_AWARDS,
        _stamp() | {"query": query, "winner_ids": winner_ids, "notices": list(map(slim_notice, notices))},
    )


def municipality_only_hit(item: dict) -> dict:
    """A RIK search hit without postal code or street: 'Harju maakond, Tallinn, ..., Kadaka tee 3/2' keeps
    'Harju maakond, Tallinn', all the connector reads."""
    county_and_municipality = ", ".join((item.get("legal_address") or "").split(", ")[:2])
    return {k: v for k, v in item.items() if k != "zip_code"} | {"legal_address": county_and_municipality}


def record_rik() -> None:
    found = check(net.get(rik.AUTOCOMPLETE, params={"q": "14117645"}, offline=False)).json()
    found["data"] = [municipality_only_hit(i) for i in found.get("data") or []]
    _write(FIXTURES / rik.LIVE_SEARCH, _stamp() | {"q": "14117645", "response": found})


SEARCHES = {"prh": "meriva", "brreg": "havnio", "rik": "avatec"}  # each finds one company of the demo set


def search_fixture(source: str) -> Path:
    return FIXTURES / "live_2026-10-17" / f"{source}_search_{SEARCHES[source]}.json"


def slim_company(company: dict) -> dict:
    """The fields the PRH connector reads, addresses kept to their municipality code."""
    slim = {
        k: company[k]
        for k in (
            "businessId",
            "names",
            "mainBusinessLine",
            "website",
            "companyForms",
            "companySituations",
            "tradeRegisterStatus",
            "addresses",
        )
        if k in company
    }
    return municipality_only(slim)


def record_search() -> None:
    """One real name search per register, kept to legal persons: sole traders are dropped before writing."""
    name = SEARCHES["prh"]
    found = check(net.get(prh.YTJ, params={"name": name}, offline=False, use_cache=False)).json()
    companies = [c for c in found.get("companies") or [] if not prh.parse_company(c).natural_person]
    _write(
        search_fixture("prh"),
        _stamp()
        | {
            "name": name,
            "response": {"totalResults": found.get("totalResults"), "companies": [slim_company(c) for c in companies]},
        },
    )
    name = SEARCHES["brreg"]
    params = {"navn": name, "size": brreg.SEARCH_SIZE, "organisasjonsform": brreg.SEARCH_FORMS}
    found = check(net.get(f"{brreg.API}/enheter", params=params, offline=False, use_cache=False)).json()
    entities = [
        slim_entity(e)
        for e in (found.get("_embedded") or {}).get("enheter") or []
        if not brreg.parse_entity(e).natural_person
    ]
    _write(
        search_fixture("brreg"),
        _stamp() | {"navn": name, "response": {"_embedded": {"enheter": entities}, "page": found.get("page")}},
    )
    name = SEARCHES["rik"]
    found = check(net.get(rik.AUTOCOMPLETE, params={"q": name}, offline=False, use_cache=False)).json()
    items = [
        municipality_only_hit(i)
        for i in found.get("data") or []
        if not rik.registry_from_search(i, None).natural_person
    ]
    _write(search_fixture("rik"), _stamp() | {"q": name, "response": {"status": found.get("status"), "data": items}})


LIVE = {"prh": record_prh, "brreg": record_brreg, "ted": record_ted, "rik": record_rik, "search": record_search}

if __name__ == "__main__":
    if sys.argv[1:2] == ["estonia"]:
        record_estonia(Path(sys.argv[2]))
    elif sys.argv[1:2] == ["live"]:
        for name in sys.argv[2:] or LIVE:
            LIVE[name]()
    else:
        raise SystemExit(__doc__)
