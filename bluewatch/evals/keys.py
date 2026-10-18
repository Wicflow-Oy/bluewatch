"""The reference set: data/seed/answer_keys.json flattened into one row per company.

The keys are bands an analyst inferred from public pages; they are not partner ratings. A band counts
only when it starts with a digit ("6-7 (inferred)"), so "unknown", "not applicable" and mixed texts are
keys that say "unknown". Investment stages are words ("pre-seed to seed", "Series A closed ...") mapped
to three stages.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from bluewatch.config import SEED_DIR

ANSWER_KEYS = SEED_DIR / "answer_keys.json"
LEVELS = ("trl", "brl", "irl")
STAGES = ("pre-seed", "seed", "Series A or later")
_WORD_BANDS = {"low": (1, 3), "medium": (4, 6), "mid": (4, 6), "high": (7, 9)}
_LEGAL_FORMS = frozenset({"oy", "oyj", "ab", "ltd", "as", "asa", "aps", "ehf", "ou", "ag", "gmbh", "ky", "inc", "llc"})


@dataclass
class KeyRow:
    group: str  # apelago | redstone | famous | partner
    name: str
    aliases: set[str] = field(default_factory=set)  # normalised names
    ids: set[str] = field(default_factory=set)  # "FI:3274823-2", "NO:924571179"
    registered: date | None = None
    bands: dict[str, tuple[int, int] | None] = field(default_factory=dict)  # trl/brl 1..9, irl stage 0..2
    texts: dict[str, str] = field(default_factory=dict)  # the key's own words


def band(text: str | None) -> tuple[int, int] | None:
    """'6-7 (inferred)' -> (6, 7); 'low' -> (1, 3); anything not starting with a level -> None."""
    text = (text or "").strip().lower()
    for word, interval in _WORD_BANDS.items():
        if text == word or text.startswith(word + " "):
            return interval
    m = re.match(r"(\d)(?:\s*-\s*(\d))?", text)
    if not m:
        return None
    lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
    return (lo, hi) if 1 <= lo <= hi <= 9 else None


def stage(text: str | None) -> tuple[int, int] | None:
    """Investment stage words -> (lo, hi) on 0 pre-seed, 1 seed, 2 Series A or later; None when unknown."""
    text = (text or "").strip().lower()
    if not text or text.startswith(("unknown", "not ", "n/a", "cannot")):
        return None
    found = set()
    if re.search(r"pre-?\s?seed", text):
        found.add(0)
    if re.search(r"\bseed", re.sub(r"pre-?\s?seed", "", text)):
        found.add(1)
    if re.search(r"series [a-f]\b|growth|late|public company|listed", text):
        found.add(2)
    return (min(found), max(found)) if found else None


def norm_name(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    words = [w for w in re.sub(r"[^a-z0-9]+", " ", plain).split() if w not in _LEGAL_FORMS]
    return " ".join(words)


def norm_id(company_id: str) -> str:
    return company_id.strip().upper().replace(" ", "")


def _aliases(*names: str | None) -> set[str]:
    out = set()
    for name in filter(None, names):
        out.add(norm_name(name))
        out.update(norm_name(part) for part in re.split(r"[()]", name) if part.strip())
    return {a for a in out if a}


def _date(text: str | None) -> date | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text or "")
    return date.fromisoformat(m.group(1)) if m else None


def _fi_ids(*texts: str | None) -> set[str]:
    return {f"FI:{i}" for t in texts if t for i in re.findall(r"\b\d{7}-\d\b", t)}


def _apelago(c: dict) -> KeyRow:
    reg = c.get("registry") or {}
    fi_text = reg.get("fi_prh") or ""
    linked = not re.search(r"no entity found|not linked|no name match", fi_text)
    ids = _fi_ids(reg.get("business_id"), fi_text if linked else None)
    no = re.search(r"organisation number (\d{9})", reg.get("brreg") or "")
    if no:
        ids.add(f"NO:{no.group(1)}")
    m = re.search(r"registered (\d{4}-\d{2}-\d{2})", f"{fi_text} {reg.get('brreg') or ''}")
    registered = date.fromisoformat(m.group(1)) if m and ids else None
    return _row("apelago", c["name"], c.get("assessment") or {}, ids, registered)


def _redstone(c: dict) -> KeyRow:
    entity = c.get("legal_entity") or {}
    ids = _fi_ids(entity.get("business_id"))
    cvr = re.search(r"CVR (\d{8})", entity.get("company_registration") or "")
    if cvr:
        ids.add(f"DK:{cvr.group(1)}")
    row = _row(
        "redstone",
        c["name"],
        c.get("assessment") or c.get("assessment_key") or {},
        ids,
        _date(entity.get("registration_date")) if ids else None,
    )
    row.aliases |= _aliases(entity.get("name"))
    return row


def _famous(c: dict) -> KeyRow:
    reg = c.get("registry") or {}
    fi, no = reg.get("fi") or {}, reg.get("no") or {}
    # A Finnish company with a separate Norwegian namesake keeps the Finnish entity (trap T9).
    primary, ids = (fi, _fi_ids(fi.get("business_id"))) if fi else (no, {f"NO:{no['org_nr']}"} if no else set())
    row = _row("famous", c["name"], c.get("assessment") or {}, ids, _date(primary.get("registered")) if ids else None)
    row.aliases |= _aliases(primary.get("name"))
    return row


def _row(group: str, name: str, assessment: dict, ids: set[str], registered: date | None) -> KeyRow:
    irl_text = assessment.get("investment_readiness_band") or assessment.get("investment_stage") or ""
    texts = {"trl": assessment.get("trl_band") or "", "brl": assessment.get("brl_band") or "", "irl": irl_text}
    bands = {"trl": band(texts["trl"]), "brl": band(texts["brl"]), "irl": stage(irl_text)}
    return KeyRow(
        group=group, name=name, aliases=_aliases(name), ids=ids, registered=registered, bands=bands, texts=texts
    )


def merge(rows: list[KeyRow]) -> list[KeyRow]:
    """One row per company: rows sharing an ID or a name are merged; the first numeric key per level wins."""
    merged: list[KeyRow] = []
    for row in rows:
        same = next((m for m in merged if m.ids & row.ids or m.aliases & row.aliases), None)
        if same is None:
            merged.append(row)
            continue
        same.ids |= row.ids
        same.aliases |= row.aliases
        same.registered = same.registered or row.registered
        for level in LEVELS:
            if same.bands.get(level) is None and row.bands.get(level) is not None:
                same.bands[level], same.texts[level] = row.bands[level], row.texts[level]
    return merged


def load_keys(path: Path | None = None) -> list[KeyRow]:
    """All answer-key rows in file group order (A'Pelago, Redstone, famous), before merging."""
    data = json.loads((path or ANSWER_KEYS).read_text(encoding="utf-8"))
    rows = [_apelago(c) for c in data["judge_known_apelago"]["companies"]]
    rows += [_redstone(c) for c in data["judge_known_redstone"]["companies"]]
    famous = data["judge_known_famous"]
    rows += [_famous(c) for c in famous["companies"] + famous.get("extra_companies", [])]
    return rows
