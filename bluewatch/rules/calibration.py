"""How the rules compare with the answer keys in the demo pack.

The keys' bands are inferred by our own researchers from public evidence, so they are a reference,
not truth, and the rules were written from the scale definitions without fitting to them. This only
measures: a level counts as exact when it falls inside the key's band, and within one when it is at
most one level outside it. Run: python -m bluewatch.rules.calibration
"""

from __future__ import annotations

import json
import re

from bluewatch import seed
from bluewatch.rules.assess import assess
from bluewatch.rules.seed_adapter import company_and_evidence


def key_band(text: str | None) -> tuple[int, int] | str | None:
    """(lo, hi) for a numeric band, "n/a" for not applicable, None for unknown or not assessed."""
    lowered = (text or "").strip().lower()
    if lowered.startswith(("not applicable", "not a technology")):
        return "n/a"
    if not lowered or lowered.startswith(("unknown", "not assessed", "none")):
        return None
    m = re.search(r"(\d)(?:\s*-\s*(\d))?", lowered)
    return (int(m.group(1)), int(m.group(2) or m.group(1))) if m else None


def answer_key_agreement(preset: str = "blue") -> dict[str, dict]:
    rows = [r for r in seed.load("startups")["startups"] if r.get("answer_key")]
    levels = {}
    too_late = {"keyed_too_late": 0, "we_say_too_late": 0}
    for row in rows:
        company, evidence, _ = company_and_evidence(row)
        a = assess(company, evidence, preset=preset)
        levels[row["name"]] = {lv.key: lv for lv in a.levels}
        if str(row["answer_key"].get("redstone_fit") or "").lower().startswith("too late"):
            too_late["keyed_too_late"] += 1
            too_late["we_say_too_late"] += "too_late" in a.flags
    report: dict[str, dict] = {"too_late_controls": too_late}
    for key in ("trl", "brl"):
        stats = {
            "n_keyed": 0,
            "answered": 0,
            "exact": 0,
            "within_one": 0,
            "abstained": 0,
            "key_unknown": 0,
            "abstained_when_key_unknown": 0,
            "key_not_applicable": 0,
            "agreed_not_applicable": 0,
        }
        for row in rows:
            band = key_band(row["answer_key"].get(f"{key}_band"))
            ours = levels[row["name"]][key]
            if band == "n/a":
                stats["key_not_applicable"] += 1
                stats["agreed_not_applicable"] += not ours.applicable
            elif band is None:
                stats["key_unknown"] += 1
                stats["abstained_when_key_unknown"] += ours.level is None
            else:
                stats["n_keyed"] += 1
                if ours.level is None:
                    stats["abstained"] += 1
                    continue
                lo, hi = band
                stats["answered"] += 1
                stats["exact"] += lo <= ours.level <= hi
                stats["within_one"] += lo - 1 <= ours.level <= hi + 1
        report[key] = stats
    return report


if __name__ == "__main__":
    print(json.dumps(answer_key_agreement(), indent=2))
