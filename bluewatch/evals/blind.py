"""Score a partner's blind set: their own calls for a few companies they assessed, against ours.

The file is CSV or JSON, one row per company: `company` (name) and/or `id` (business ID or "FI:..."),
optional `country`, and any of `trl`, `brl` (a level, a band like 4-6, or low / medium / high) and
`stage` (investment stage words). Empty or "unknown" means they would not commit. With only 3-5 rows
the report lists every company side by side in its notes; kappa needs at least 10.
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

from bluewatch.evals.keys import STAGES, KeyRow, band, norm_name, stage
from bluewatch.evals.precision import Match, band_of, engine_value, level_of, match, report, within_one
from bluewatch.models import Assessment, Company, PrecisionReport

_SHOWN = {"trl": "TRL", "brl": "BRL", "irl": "stage"}


def load_blind_set(path: Path) -> list[KeyRow]:
    return parse_blind_set(path.read_text(encoding="utf-8-sig"), json_format=path.suffix.lower() == ".json")


def parse_blind_set(text: str, *, json_format: bool = False) -> list[KeyRow]:
    """Rows from CSV or JSON text; the API passes an upload here so it never touches the disk."""
    text = text.lstrip("\ufeff")
    if json_format:
        data = json.loads(text)
        records = data["companies"] if isinstance(data, dict) else data
    else:
        lines = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        records = list(csv.DictReader(io.StringIO(lines)))
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise ValueError("Each row must be an object with a company name and its levels.")
    rows = []
    for record in records:
        r = {str(k).strip().lower(): str(v or "").strip() for k, v in record.items()}
        name = r.get("company") or r.get("name") or r.get("id") or ""
        texts = {"trl": r.get("trl", ""), "brl": r.get("brl", ""), "irl": r.get("stage", "")}
        rows.append(
            KeyRow(
                group="partner",
                name=name,
                aliases={norm_name(name)} - {""},
                ids=_ids(r),
                bands={"trl": band(texts["trl"]), "brl": band(texts["brl"]), "irl": stage(texts["irl"])},
                texts=texts,
            )
        )
    return rows


def score_blind_set(
    path: Path | str,
    *,
    assessments: Iterable[Assessment] | Mapping[str, Assessment] | None = None,
    companies: Iterable[Company] = (),
) -> PrecisionReport:
    """Our assessments against the partner's rows. Without `assessments`, the demo pipeline's are used."""
    path = Path(path)
    return score_blind_rows(load_blind_set(path), name=path.name, assessments=assessments, companies=companies)


def score_blind_rows(
    rows: list[KeyRow],
    *,
    name: str,
    assessments: Iterable[Assessment] | Mapping[str, Assessment] | None = None,
    companies: Iterable[Company] = (),
) -> PrecisionReport:
    if assessments is None:
        from bluewatch import demo

        data = demo.build()
        assessments, companies = data.assessments, list(data.companies.values())
    companies = list(companies)
    if not isinstance(assessments, Mapping):
        assessments = list(assessments)  # used twice: for the report and for the side-by-side rows
    result = report(
        assessments,
        keys=rows,
        blind=True,
        companies=companies,
        with_traps=False,
        reference=f"{name}: {len(rows)} {'company' if len(rows) == 1 else 'companies'} from your own assessments",
    )
    result.notes += [_side_by_side(m) for m in match(rows, assessments, companies)]
    return result


def _ids(r: dict[str, str]) -> set[str]:
    raw = r.get("id", "").upper()
    if not raw:
        return set()
    if ":" in raw:
        return {raw}
    country = r.get("country", "").upper() or ("FI" if re.fullmatch(r"\d{7}-\d", raw) else "NO")
    return {f"{country}:{raw}"}


def _side_by_side(m: Match) -> str:
    if m.assessment is None:
        return f"Partner row {m.row.name}: not in our assessments."
    parts = []
    for key, shown in _SHOWN.items():
        theirs = m.row.bands.get(key)
        ours = engine_value(key, level_of(m.assessment, key))
        if theirs is None and ours is None:
            continue
        ours_text = "unknown" if ours is None else (STAGES[ours] if key == "irl" else str(ours))
        theirs_text = "unknown" if theirs is None else _band_text(key, theirs)
        verdict = ""
        if ours is not None and theirs is not None:
            same = band_of(key, ours) == band_of(key, theirs[0]) == band_of(key, theirs[1])
            verdict = " (same band)" if same else " (within one)" if within_one(key, ours, theirs) else " (differs)"
        parts.append(f"{shown} ours {ours_text} / yours {theirs_text}{verdict}")
    return f"Partner row {m.row.name}: " + ("; ".join(parts) or "no calls on either side") + "."


def _band_text(key: str, interval: tuple[int, int]) -> str:
    if key == "irl":
        return " to ".join(dict.fromkeys(STAGES[i] for i in interval))
    return str(interval[0]) if interval[0] == interval[1] else f"{interval[0]}-{interval[1]}"
