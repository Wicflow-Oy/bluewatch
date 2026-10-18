"""Estonia: e-Business Register (RIK) daily open-data files (CC BY 4.0) and its public search box for lookups.

New companies: the simple CSV gives the first-entry date (ettevotja_esmakande_kpv); EMTAK activity codes come
from the general JSON file (4.6 GB unzipped, streamed line by line) or from a cached extract of it. Contact
data in the general file (e-mail, phones) is never read. Sole traders (FIE) are people and are skipped.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import re
import zipfile
from collections.abc import Callable, Iterator
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from bluewatch import net, seed
from bluewatch.config import DATA_DIR, USER_AGENT, settings
from bluewatch.models import ConnectorResult, EntityRef, Registry, Signal
from bluewatch.sources.common import (
    FIXTURES,
    SEARCH_TIMEOUT_S,
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
    source_status,
    span_label,
    unavailable,
)

SOURCE = "rik"
FILES_URL = "https://avaandmed.ariregister.rik.ee/sites/default/files/avaandmed/"
SIMPLE_CSV = "ettevotja_rekvisiidid__lihtandmed.csv.zip"
GENERAL_JSON = "ettevotja_rekvisiidid__yldandmed.json.zip"
DOWNLOADS = DATA_DIR / "downloads" / "ee"
AUTOCOMPLETE = "https://ariregister.rik.ee/est/api/autocomplete"  # the register's own search box, keyless
RECORDED = "rik_new_companies_2026-08-22_2026-10-16.json"
INDEX = "rik_index_2026-10-17.tsv.gz"
LIVE_SEARCH = "live_2026-10-17/rik_autocomplete_14117645.json"
REG_CODE = re.compile(r"^\d{8}$")
RECORDED_COLUMNS = ["id", "name", "founded", "form", "industry_code", "municipality", "website", "status"]

FORMS = {
    "Osaühing": "OÜ",
    "Aktsiaselts": "AS",
    "Füüsilisest isikust ettevõtja": "FIE",
    "Mittetulundusühing": "MTÜ",
    "Korteriühistu": "KÜ",
    "Usaldusühing": "UÜ",
    "Täisühing": "TÜ",
    "Tulundusühistu": "TÜH",
    "Sihtasutus": "SA",
    "Välismaa äriühingu filiaal": "filiaal",
    "Euroopa äriühing (Societas Europaea)": "SE",
}
STATUS = {"R": "registered", "L": "in liquidation", "N": "bankrupt", "K": "deleted"}
# The search box reports the legal form as a number; only codes we have seen are trusted.
SEARCH_FORMS = {"5": "OÜ"}
# Legal persons carry their form in the name ("Avatec Marine OÜ"); a sole trader's name is just a person's name.
NAME_FORM = re.compile(r"\b(OÜ|AS|MTÜ|SA|TÜ|UÜ|KÜ|TÜH|SE)\b|(osaühing|aktsiaselts|sihtasutus|ühistu|ühing)", re.I)
NAME_WORDS = {"osaühing": "OÜ", "aktsiaselts": "AS", "sihtasutus": "SA"}


# --------------------------------------------------------------------------- parsing
def _municipality(location: str | None) -> str | None:
    """'Kesklinna linnaosa, Tallinn, Harju maakond' -> 'Tallinn'; 'Harju maakond, Tallinn, ...' -> 'Tallinn'.
    Only the municipality leaves here: a part with a digit is a street or postal code, so it gives None."""
    parts = [p.strip() for p in (location or "").split(",") if p.strip()]
    if len(parts) >= 2 and parts[0].endswith("maakond"):
        name = parts[1]
    elif len(parts) >= 2:
        name = parts[-2]
    else:
        name = parts[0] if parts and not parts[0].endswith("maakond") else None
    return None if name is None or any(c.isdigit() for c in name) else name


def _csv_rows(simple_csv_zip: Path) -> Iterator[dict]:
    with zipfile.ZipFile(simple_csv_zip) as archive, archive.open(archive.infolist()[0]) as raw:
        yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter=";")


def registry_from_row(row: dict, codes: dict | None = None) -> Registry:
    """One row of the simple CSV, with EMTAK codes when known. A missing code stays None."""
    vorm = row.get("ettevotja_oiguslik_vorm") or ""
    known = codes or {}
    record = Registry(
        country="EE",
        id=row["ariregistri_kood"],
        name=row.get("nimi") or None,
        founded=parse_date(row.get("ettevotja_esmakande_kpv")),
        form=FORMS.get(vorm, vorm or None),
        industry_code=(known.get("emtak") or [None])[0],
        industry_scheme="EMTAK" if known.get("emtak") else None,
        municipality=_municipality(row.get("asukoha_ehak_tekstina")),
        website=known.get("website"),
        status=STATUS.get(row.get("ettevotja_staatus") or ""),
    )
    return private_person(record) if record.form == "FIE" else record


def newly_founded(record: Registry, seen_at: datetime) -> Signal:
    return make_signal(
        SOURCE,
        "newly_founded",
        EntityRef(registry="rik", id=record.id, name=record.name),
        key=record.id,
        event_date=record.founded,
        first_seen_at=seen_at,
        url=f"https://ariregister.rik.ee/est/company/{record.id}",
        title=f"New company: {record.name}",
        payload={"form": record.form, "industry_code": record.industry_code},
    )


# --------------------------------------------------------------------------- activity codes
def _codes_of(company: dict) -> dict:
    """Active EMTAK codes (main first) and the website domain. E-mail and phone entries are skipped unread."""
    general = company.get("yldandmed") or {}
    active = [a for a in general.get("teatatud_tegevusalad") or [] if a.get("emtak_kood") and not a.get("lopp_kpv")]
    active.sort(key=lambda a: not a.get("on_pohitegevusala"))
    sites = [str(c.get("sisu")) for c in general.get("sidevahendid") or [] if c.get("liik") == "WWW" and c.get("sisu")]
    host = re.sub(r"^https?://", "", sites[0].strip(), flags=re.I).split("/")[0].lower() if sites else None
    return {"emtak": [str(a["emtak_kood"]) for a in active], "website": host}


def stream_codes(general_json_zip: Path, wanted: set[str]) -> dict[str, dict]:
    """Read EMTAK codes for the wanted registry codes from the general JSON file without loading it whole.

    The file is one JSON array with one company object per block of lines ("    {" ... "    }").
    """
    found: dict[str, dict] = {}
    with zipfile.ZipFile(general_json_zip) as archive, archive.open(archive.infolist()[0]) as raw:
        block: list[str] | None = None
        keep: bool | None = None
        for line in io.TextIOWrapper(raw, encoding="utf-8"):
            if block is None:
                if line.startswith("    {"):
                    block, keep = [line], None
                continue
            if keep is None and '"ariregistri_kood"' in line:
                keep = line.split(":", 1)[1].strip().strip(",").strip('"') in wanted
            if keep is not False:
                block.append(line)
            if line.startswith("    }"):
                if keep:
                    company = json.loads("".join(block).rstrip().rstrip(","))
                    found[str(company["ariregistri_kood"])] = _codes_of(company)
                block = None
    return found


# --------------------------------------------------------------------------- new companies
def _file_date(path: Path) -> datetime:
    with zipfile.ZipFile(path) as archive:
        return datetime(*archive.infolist()[0].date_time, tzinfo=timezone.utc)


def load_new_companies(
    since: date,
    until: date,
    *,
    simple_csv_zip: Path,
    general_json_zip: Path | None = None,
    codes_cache: Path | None = None,
) -> ConnectorResult:
    """Legal persons first entered in the window; sole traders (FIE) are counted and skipped."""
    try:
        rows = [
            r
            for r in _csv_rows(simple_csv_zip)
            if in_window(parse_date(r.get("ettevotja_esmakande_kpv")), since, until)
        ]
        people = sum(1 for r in rows if FORMS.get(r.get("ettevotja_oiguslik_vorm") or "") == "FIE")
        rows = [r for r in rows if FORMS.get(r.get("ettevotja_oiguslik_vorm") or "") != "FIE"]
        if general_json_zip:
            codes = stream_codes(general_json_zip, {r["ariregistri_kood"] for r in rows})
        elif codes_cache:
            codes = json.loads(Path(codes_cache).read_text(encoding="utf-8"))["codes"]
        else:
            codes = {}
        file_date = _file_date(simple_csv_zip)
    except (OSError, zipfile.BadZipFile, KeyError, ValueError) as exc:  # the boundary: a bad file is reported
        return ConnectorResult(status=failed(SOURCE, "daily file", exc))
    records = [registry_from_row(r, codes.get(r["ariregistri_kood"])) for r in rows]
    coded = sum(1 for r in records if r.industry_code)
    detail = (
        f"daily file of {file_date:%d %b %Y}: {len(records)} legal persons first entered "
        f"{span_label(since, until)}, {coded} with EMTAK codes; {people} sole traders (FIE) skipped"
    )
    if not codes:
        detail += "; activity codes not loaded, so codes are unknown, not missing"
    status = source_status(SOURCE, "daily_file", records=len(records), detail=detail, data_as_of=file_date)
    seen_at = now()
    return ConnectorResult(records=records, signals=[newly_founded(r, seen_at) for r in records], status=status)


def _recorded_new_companies(since: date, until: date) -> ConnectorResult:
    data = seed.fixture(f"sources/{RECORDED}")
    start, end = parse_date(data["since"]), parse_date(data["until"])
    if until < start or since > end:
        return ConnectorResult(
            status=unavailable(SOURCE, f"offline and no recorded daily file for {span_label(since, until)}")
        )
    recorded_at = fixture_time(data["recorded_at"])
    rows = [dict(zip(data["columns"], row, strict=True)) for row in data["rows"]]
    records = [
        Registry(country="EE", industry_scheme="EMTAK" if r["industry_code"] else None, **r)
        for r in rows
        if in_window(parse_date(r["founded"]), since, until)
    ]
    detail = (
        f"recorded extract of the {data['file_date']} daily file: all legal persons first entered "
        f"{span_label(start, end)}"
    )
    if since < start or until > end:
        detail += "; other days in the window were not recorded (not counted as zero)"
    status = source_status(SOURCE, "cached", records=len(records), detail=detail, data_as_of=recorded_at)
    return ConnectorResult(records=records, signals=[newly_founded(r, recorded_at) for r in records], status=status)


def fetch_new_companies(since: date, until: date) -> ConnectorResult:
    """The feed's entry point: today's downloaded daily files when present, else the recorded extract."""
    simple = DOWNLOADS / SIMPLE_CSV
    if not simple.exists():
        return _recorded_new_companies(since, until)
    general = DOWNLOADS / GENERAL_JSON
    return load_new_companies(
        since, until, simple_csv_zip=simple, general_json_zip=general if general.exists() else None
    )


# --------------------------------------------------------------------------- lookup
def build_index(simple_csv_zip: Path, out: Path) -> int:
    """A compact lookup index of legal persons (company-level fields only, no contact data, no sole traders)."""
    count = 0
    with gzip.open(out, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["reg_code", "form", "status", "first_entry", "municipality", "name"])
        for row in sorted(_csv_rows(simple_csv_zip), key=lambda r: r["ariregistri_kood"]):
            record = registry_from_row(row)
            if record.natural_person:
                continue
            writer.writerow(
                [
                    record.id,
                    record.form or "",
                    record.status or "",
                    record.founded.isoformat() if record.founded else "",
                    record.municipality or "",
                    record.name or "",
                ]
            )
            count += 1
    return count


def _index_rows() -> Iterator[list[str]]:
    """The compressed index, row by row: reg_code, form, status, first_entry, municipality, name."""
    with gzip.open(FIXTURES / INDEX, "rt", encoding="utf-8", newline="") as fh:
        rows = csv.reader(fh, delimiter="\t")
        next(rows)  # header
        yield from rows


def _index_record(row: list[str]) -> Registry:
    reg_code, form, status, first_entry, municipality, name = row
    return Registry(
        country="EE",
        id=reg_code,
        name=name or None,
        founded=parse_date(first_entry),
        form=form or None,
        status=status or None,
        municipality=municipality or None,
    )


def _index_lookup(code: str) -> Registry | None:
    """Scan the index (sorted by code) and stop at the first match or past it."""
    for row in _index_rows():
        if row[0] == code:
            return _index_record(row)
        if row[0] > code:  # codes are 8 digits, so text order is number order
            return None
    return None


def _index_find(keep: Callable[[list[str]], bool]) -> list[Registry]:
    """Every indexed legal person whose row passes `keep`, in one pass over the index."""
    if not (FIXTURES / INDEX).exists():
        return []
    return [_index_record(row) for row in _index_rows() if keep(row)]


def _form_in_name(name: str | None) -> str | None:
    match = NAME_FORM.search(name or "")
    if match is None:
        return None
    return match.group(1).upper() if match.group(1) else NAME_WORDS.get(match.group(2).lower(), "legal person")


def registry_from_search(item: dict, known: Registry | None) -> Registry:
    """A search-box hit. Without a trusted legal form the record is treated as a sole trader and kept private."""
    name = item.get("name")
    form = (known.form if known else None) or SEARCH_FORMS.get(str(item.get("legal_form"))) or _form_in_name(name)
    record = Registry(
        country="EE",
        id=str(item["reg_code"]),
        name=name,
        form=form,
        founded=known.founded if known else None,
        status=STATUS.get(item.get("status") or ""),
        municipality=_municipality(item.get("legal_address")),
    )
    return record if form and form != "FIE" else private_person(record)


def lookup_result(code: str, *, offline: bool | None = None) -> ConnectorResult:
    """Look one Estonian registry code up; the status says whether the answer is live or from the index."""
    code = code.strip()
    if not REG_CODE.match(code):
        return ConnectorResult(status=unavailable(SOURCE, "not an Estonian registry code (8 digits)"))
    known = _index_lookup(code) if (FIXTURES / INDEX).exists() else None
    if go_live(offline, lookup=True):
        try:
            data = check(net.get(AUTOCOMPLETE, params={"q": code}, offline=False, use_cache=False)).json()
        except Exception as exc:  # the boundary: a failed lookup is reported, never shown as "not found"
            return ConnectorResult(status=failed(SOURCE, "register search", exc))
        hits = [registry_from_search(i, known) for i in data.get("data") or [] if str(i.get("reg_code")) == code]
        detail = "looked up live in the register's search" if hits else "no entity with this code in the register"
        return ConnectorResult(
            records=hits[:1], status=source_status(SOURCE, "live", records=len(hits[:1]), detail=detail)
        )
    if known is None:
        return ConnectorResult(
            status=unavailable(
                SOURCE, "live lookups are off and this code is not in the recorded index of legal persons"
            )
        )
    return ConnectorResult(
        records=[known],
        status=source_status(
            SOURCE, "cached", records=1, detail="live lookups are off; index of the 17 Oct 2026 daily file"
        ),
    )


def lookup(code: str, *, offline: bool | None = None) -> Registry | None:
    found = lookup_result(code, offline=offline).records
    return found[0] if found else None


# --------------------------------------------------------------------------- name search
def _name_in_index(name: str) -> Callable[[list[str]], bool]:
    words = name.casefold().split()

    def keep(row: list[str]) -> bool:
        folded = row[5].casefold()  # a cheap substring test first: the index holds about 355,000 names
        return all(w in folded for w in words) and name_rank(name, row[5]) is not None

    return keep


def search_result(name: str, *, offline: bool | None = None) -> ConnectorResult:
    """Legal persons whose name matches, from the register's own search box (at most 10 hits) or offline from the
    index of the daily file. Founding dates come from the index. The live call skips every cache."""
    if go_live(offline, lookup=True):
        try:
            data = check(
                net.get(AUTOCOMPLETE, params={"q": name}, offline=False, use_cache=False, timeout_s=SEARCH_TIMEOUT_S)
            ).json()
            items = data.get("data") or []
            codes = {str(i.get("reg_code")) for i in items}
            known = {r.id: r for r in _index_find(lambda row: row[0] in codes)}
            records = [registry_from_search(i, known.get(str(i["reg_code"]))) for i in items]
        except Exception as exc:  # the boundary: a failed search is reported, never shown as "no match"
            return ConnectorResult(status=failed(SOURCE, "register search", exc))
        return ConnectorResult(
            records=records,
            status=source_status(SOURCE, "live", records=len(records), detail="searched live in the register's search"),
        )
    records = _index_find(_name_in_index(name))
    return ConnectorResult(
        records=records,
        status=source_status(
            SOURCE,
            "cached",
            records=len(records),
            detail="live lookups are off; searched the index of the 17 Oct 2026 daily file",
        ),
    )


# --------------------------------------------------------------------------- downloads
def download_daily_files(dest: Path = DOWNLOADS, *, confirm: bool = False) -> list[tuple[str, int | None]]:
    """Print the two daily files and their sizes; download them only with confirm=True (they are large)."""
    if settings().offline:
        raise net.OfflineError("downloads need BLUEWATCH_OFFLINE=0")
    files = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True) as client:
        for name in (SIMPLE_CSV, GENERAL_JSON):
            size = client.head(FILES_URL + name).headers.get("content-length")
            files.append((name, int(size) if size else None))
            print(f"{name}: {int(size) / 1e6:.1f} MB" if size else f"{name}: size unknown")
        if not confirm:
            print("Not downloaded. Run again with confirm=True to download.")
            return files
        dest.mkdir(parents=True, exist_ok=True)
        for name, _ in files:
            with client.stream("GET", FILES_URL + name) as resp, open(dest / name, "wb") as out:
                resp.raise_for_status()
                for chunk in resp.iter_bytes(1 << 20):
                    out.write(chunk)
    return files
