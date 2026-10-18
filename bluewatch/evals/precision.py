"""Precision: how often our readiness calls match the reference keys, with the age baseline beside every
number, because a call that only tracks company age is no skill. Every number is computed here from the
assessments and the keys.

- n: companies we answered whose key sits inside one band (1-3 / 4-6 / 7-9). Keys that straddle a
  band edge ("6-7") are left out of n and counted in the notes.
- exact: the same band. within one: within one level of the key's band. weighted kappa: quadratic on
  the three bands, only when n >= 10.
- age baseline: the band from company age alone, scored on the same n companies.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from bluewatch.config import DATA_DIR, settings
from bluewatch.evals.keys import ANSWER_KEYS, LEVELS, STAGES, KeyRow, load_keys, merge, norm_id, norm_name
from bluewatch.evals.stats import kappa_interval, qwk, wilson
from bluewatch.evals.traps import run_traps
from bluewatch.models import Assessment, Company, LevelAgreement, PrecisionReport, ReadinessLevel

FROZEN_PATH = DATA_DIR / "eval" / "precision" / "frozen.json"
BANDS = ("1-3", "4-6", "7-9")
AGE_EDGES = (5.0, 9.5)  # years; fitted on these same keys, so the baseline is optimistic
MIN_N_KAPPA = 10
LEVEL_NAMES = {"trl": "Tech readiness (TRL)", "brl": "Business readiness (BRL)", "irl": "Investment readiness"}
METHOD_NOTES = [
    "Age baseline: the band from company age alone (under 5 years 1-3, 5 to 9.5 years 4-6, older 7-9; for "
    "investment readiness pre-seed, seed, Series A or later), from the register date in the key. It is scored on "
    "the same companies as ours; where the age is unknown it abstains and counts as a miss.",
    "Investment readiness: our 1-9 scale maps to stages (1-6 pre-seed, 7-8 seed, 9 Series A or later); late-stage "
    "and public companies in the keys fall in the top stage.",
    "Ocean impact: our own 1-5 scale, uncalibrated. No reference keys exist, so n = 0.",
]


@dataclass
class Match:
    row: KeyRow
    assessment: Assessment | None
    age: float | None  # years at `today`, from the register date


def match(
    rows: list[KeyRow],
    assessments: Iterable[Assessment] | Mapping[str, Assessment],
    companies: Iterable[Company] = (),
    today: date | None = None,
) -> list[Match]:
    """Pair each key row with its assessment: by register ID first, then by name."""
    today = today or settings().today
    by_name: dict[str, Assessment] = {}
    if isinstance(assessments, Mapping):
        by_name = {norm_name(name): a for name, a in assessments.items()}
        assessments = list(assessments.values())
    by_id = {norm_id(a.company_id): a for a in assessments}
    founded: dict[str, date] = {}
    for company in companies:
        if norm_id(company.id) in by_id:
            for name in company.names:
                by_name.setdefault(norm_name(name), by_id[norm_id(company.id)])
        if company.resolution.state == "resolved" and company.registry.founded:
            founded[norm_id(company.id)] = company.registry.founded
    out = []
    for row in rows:
        found = next((by_id[i] for i in sorted(row.ids) if i in by_id), None)
        found = found or next((by_name[a] for a in sorted(row.aliases) if a in by_name), None)
        start = row.registered or (founded.get(norm_id(found.company_id)) if found else None)
        out.append(Match(row, found, (today - start).days / 365.25 if start else None))
    return out


def report(
    assessments: Iterable[Assessment] | Mapping[str, Assessment],
    *,
    keys: list[KeyRow] | Path | None = None,
    blind: bool = False,
    companies: Iterable[Company] = (),
    today: date | None = None,
    rules_hash: str | None = None,
    with_traps: bool = True,
    frozen_path: Path = FROZEN_PATH,
    reference: str | None = None,
) -> PrecisionReport:
    if keys is None or isinstance(keys, Path):
        raw = load_keys(keys)
        rows = merge(raw)
        reference = reference or (
            f"{len(rows)} companies with reference answers ({len(raw) - len(rows)} duplicate "
            "rows merged), bands inferred by an analyst from public pages, not your team's "
            "ratings"
        )
    else:
        rows = keys
    matches = match(rows, assessments, companies, today)
    matched = sum(1 for m in matches if m.assessment)
    notes = [
        f"Reference: {reference or 'given key rows'}.",
        f"Matched {matched} of {len(rows)} reference companies to an assessment; the rest were not scored.",
        *METHOD_NOTES,
    ]
    levels = []
    for key in LEVELS:
        agreement, level_notes = _agreement(key, matches)
        levels.append(agreement)
        notes += level_notes
    levels.append(LevelAgreement(key="oirl", n=0, exact=0, within_one=0))

    traps = run_traps() if with_traps else None
    if with_traps and traps is None:
        notes.append("Entity traps did not run: the company matcher is not available in this build.")
    elif traps:
        notes.append(f"Entity traps: {sum(t.passed for t in traps)} of {len(traps)} passed.")

    rules_hash = rules_hash or _rules_hash_of([m.assessment for m in matches if m.assessment], notes)
    return PrecisionReport(
        generated_at=datetime.now(timezone.utc),
        rules_hash=rules_hash,
        frozen_at=_frozen_at(frozen_path, rules_hash, notes),
        blind=blind,
        reference=reference or "",
        levels=levels,
        traps=traps or [],
        notes=notes,
    )


def freeze(path: Path = FROZEN_PATH, *, rules_hash: str | None = None, now: datetime | None = None) -> dict:
    """Record the rules hash and the time, so a later run can show it used the frozen rules."""
    record = {
        "rules_hash": rules_hash or current_rules_hash(),
        "frozen_at": (now or datetime.now(timezone.utc)).isoformat(),
        "answer_keys_sha256": hashlib.sha256(ANSWER_KEYS.read_bytes()).hexdigest(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def current_rules_hash() -> str:
    try:
        from bluewatch.rules.version import rules_version
    except ImportError as exc:
        raise RuntimeError("bluewatch.rules.version is not importable; pass rules_hash explicitly") from exc
    return rules_version()


def engine_value(key: str, level: ReadinessLevel | None) -> int | None:
    """Our answer on the key's scale: TRL/BRL 1-9, investment readiness as a stage 0-2; None = abstained."""
    if level is None or level.level is None or not level.applicable:
        return None
    if key == "irl":
        return 0 if level.level <= 6 else 1 if level.level <= 8 else 2
    return level.level


def band_of(key: str, value: int) -> int:
    return value if key == "irl" else 0 if value <= 3 else 1 if value <= 6 else 2


def within_one(key: str, value: int, interval: tuple[int, int]) -> bool:
    return interval[0] - 1 <= value <= interval[1] + 1


def level_of(assessment: Assessment | None, key: str) -> ReadinessLevel | None:
    return next((lv for lv in assessment.levels if lv.key == key), None) if assessment else None


def _key_band(key: str, interval: tuple[int, int]) -> int | None:
    lo, hi = band_of(key, interval[0]), band_of(key, interval[1])
    return lo if lo == hi else None


def _age_value(key: str, age: float | None) -> int | None:
    if age is None:
        return None
    b = 0 if age < AGE_EDGES[0] else 1 if age < AGE_EDGES[1] else 2
    return b if key == "irl" else b * 3 + 2  # the middle level of the age band


def _agreement(key: str, matches: list[Match]) -> tuple[LevelAgreement, list[str]]:
    labels = STAGES if key == "irl" else BANDS
    keyed = [m for m in matches if m.assessment and m.row.bands.get(key)]
    answered = [(m, v) for m in keyed if (v := engine_value(key, level_of(m.assessment, key))) is not None]
    scored = [(m, v, kb) for m, v in answered if (kb := _key_band(key, m.row.bands[key])) is not None]
    truth = [kb for _, _, kb in scored]
    pred = [band_of(key, v) for _, v, _ in scored]
    n = len(scored)
    exact = sum(t == p for t, p in zip(truth, pred, strict=True))
    within = sum(within_one(key, v, m.row.bands[key]) for m, v, _ in scored)
    kappa = qwk(truth, pred) if n >= MIN_N_KAPPA else None
    ages = [(m, _age_value(key, m.age), kb) for m, _, kb in scored]
    base_exact = sum(1 for _, b, kb in ages if b is not None and band_of(key, b) == kb)
    base_within = sum(1 for m, b, _ in ages if b is not None and within_one(key, b, m.row.bands[key]))
    agreement = LevelAgreement(
        key=key,
        n=n,
        exact=exact,
        within_one=within,
        weighted_kappa=kappa,
        confusion={
            labels[i]: {
                labels[j]: sum(1 for t, p in zip(truth, pred, strict=True) if (t, p) == (i, j)) for j in range(3)
            }
            for i in range(3)
        },
        baseline_exact=base_exact,
        baseline_within_one=base_within,
    )

    name = LEVEL_NAMES[key]
    if not keyed:
        return agreement, [f"{name}: none of the matched companies has a numeric key."]
    straddlers = [(m, v) for m, v in answered if _key_band(key, m.row.bands[key]) is None]
    unknown_keys = [m for m in matches if m.assessment and not m.row.bands.get(key)]
    abstained = sum(1 for m in unknown_keys if engine_value(key, level_of(m.assessment, key)) is None)
    confident = [(m, v) for m, v in answered if level_of(m.assessment, key).confidence == "high"]
    confident_wrong = sum(1 for m, v in confident if not within_one(key, v, m.row.bands[key]))
    kappa_text = (
        f"{kappa}{_interval(kappa_interval(truth, pred))}"
        if kappa is not None
        else f"not computed (n < {MIN_N_KAPPA} or one band only)"
    )
    groups = Counter(m.row.group for m, _, _ in scored)
    group_exact = Counter(m.row.group for m, v, kb in scored if band_of(key, v) == kb)
    straddle = "straddles a band edge and is" if len(straddlers) == 1 else "straddle a band edge and are"
    notes = [
        f"{name}: exact {exact} of {n}{_interval(wilson(exact, n))}, within one {within} of {n}"
        f"{_interval(wilson(within, n))}, weighted kappa {kappa_text}. Age baseline on the same {n}: exact "
        f"{base_exact}, within one {base_within} (age known for {sum(b is not None for _, b, _ in ages)}).",
        f"{name}: we answered {len(answered)} of {_companies(len(keyed))} with a numeric key; {len(straddlers)} of "
        f"those keys {straddle} left out of n (within one on them: "
        f"{sum(within_one(key, v, m.row.bands[key]) for m, v in straddlers)}). We abstained on {abstained} of "
        f"{_companies(len(unknown_keys))} whose key says unknown. High-confidence answers more than one level off: "
        f"{confident_wrong} of {len(confident)}.",
    ]
    if groups:
        notes.append(f"{name}: exact by group: " + ", ".join(f"{g} {group_exact[g]} of {c}" for g, c in groups.items()))
    return agreement, notes


def _companies(n: int) -> str:
    return "1 company" if n == 1 else f"{n} companies"


def _interval(ci: tuple[float, float] | None) -> str:
    return f" [95% CI {ci[0]}-{ci[1]}]" if ci else ""


def _rules_hash_of(assessments: list[Assessment], notes: list[str]) -> str:
    versions = sorted({a.rules_version for a in assessments})
    if len(versions) > 1:
        notes.append(f"The assessments carry {len(versions)} different rules versions: {', '.join(versions)}.")
    if len(versions) == 1:
        return versions[0]
    try:
        return current_rules_hash()
    except RuntimeError:
        return "unknown"


def _frozen_at(path: Path, rules_hash: str, notes: list[str]) -> datetime | None:
    if not path.exists():
        notes.append("The rules have not been frozen yet, so this is a development run.")
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if record["rules_hash"] != rules_hash:
        notes.append(
            f"The rules changed since the freeze at {record['frozen_at']} (frozen {record['rules_hash']}, "
            f"now {rules_hash}), so this is not a frozen result."
        )
        return None
    return datetime.fromisoformat(record["frozen_at"])
