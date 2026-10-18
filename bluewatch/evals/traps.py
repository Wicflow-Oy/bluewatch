"""The "wrong company" test: the ten entity-resolution traps run against the real resolver.

The cases live in data/eval/precision/traps.json. A trap fails when the resolver accepts the wrong
company, lands in a state the case does not allow, or hides the right company from the first three
candidates, because a reviewer only looks at the top few.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from bluewatch.config import DATA_DIR
from bluewatch.models import Candidate, Registry, Resolution, TrapResult

TRAPS_PATH = DATA_DIR / "eval" / "precision" / "traps.json"
Resolve = Callable[..., Resolution]


def load_cases() -> list[dict]:
    return json.loads(TRAPS_PATH.read_text(encoding="utf-8"))["cases"]


def run_traps(resolve: Resolve | None = None) -> list[TrapResult] | None:
    """All trap results, or None when the resolver is not importable yet."""
    if resolve is None:
        try:
            from bluewatch.resolve.resolver import resolve
        except ImportError:
            return None
    return [judge(case, resolve) for case in load_cases()]


def judge(case: dict, resolve: Resolve) -> TrapResult:
    given, expect = case["input"], case["expect"]
    candidates = [
        Candidate(name=c["name"], registry=Registry(**c["registry"]), score=0.0, reason="recorded register search")
        for c in given.get("candidates", [])
    ]
    label = f"{case['id']} {case['name']}"
    try:
        result = resolve(
            given["name"],
            country=given["country"],
            registry_id=given.get("registry_id"),
            domain=given.get("domain"),
            page_ids=tuple(given.get("page_ids", [])),
            candidates=candidates,
        )
    except Exception as exc:  # a crash is a failed trap: reported on the Precision screen, never hidden
        return TrapResult(
            case=label, expected=expect["text"], got=f"error: {type(exc).__name__}", passed=False, note=str(exc)[:200]
        )

    shown = [c.registry.id for c in result.candidates[:3]]
    accepted = None
    if result.state in ("resolved", "probable"):
        accepted = shown[0] if shown else given.get("registry_id")
    gold = _id(expect["gold"]) if expect["gold"] else None
    problems = []
    if result.state not in expect["ok_states"]:
        problems.append(f"'{result.state}' is not an allowed outcome")
    if accepted and (_id(accepted) in {_id(i) for i in expect["must_not_accept"]} or (gold and _id(accepted) != gold)):
        problems.append(f"accepted the wrong company ({accepted})")
    if result.state in ("ambiguous", "unconfirmed") and gold and gold not in {_id(i) for i in shown}:
        problems.append("the right company is not among the first three candidates")
    got = result.state + (f": {accepted}" if accepted else "") + (f" (listed {', '.join(shown)})" if shown else "")
    return TrapResult(
        case=label, expected=expect["text"], got=got, passed=not problems, note="; ".join(problems) or case["trap"]
    )


def _id(value: str) -> str:
    """IDs compare without separators or country prefixes: 'FI:2902007-2' == '29020072'."""
    return re.sub(r"[^0-9a-z]", "", value.lower().split(":")[-1])
