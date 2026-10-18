"""List every English sentence pattern the API can translate into data/i18n/source.json, the input for fi/sv.json.

Runs every precomputed output through the API (both workspaces, both presets, every card, the founder
view, Idea Harbour's form, rubric, live queue and sample-data queue, the outreach desk's sending rules)
and keeps the values of the fields bluewatch/i18n.py translates, as patterns with their numbers replaced
by slots ("Deadline {0} Oct {1}, in {2} days"). Countdowns and ages change wording near zero ("today",
"tomorrow") and dates change month, so it collects today and the following days (a week by default).
Offline and reproducible; run from the repo root after any rules or data change:

    .venv/bin/python scripts/collect_strings.py [days, default 7]
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Offline and reproducible: recorded data only, no keys, no live lookups.
os.environ.update({"BLUEWATCH_SKIP_ENV_LOCAL": "1", "BLUEWATCH_OFFLINE": "1", "BLUEWATCH_LIVE_LOOKUPS": "0"})
os.environ.pop("ANTHROPIC_API_KEY", None)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from bluewatch.api import app as app_module  # noqa: E402
from bluewatch.api import deps  # noqa: E402
from bluewatch.api.guards import RateLimiter  # noqa: E402
from bluewatch.api.ideas import idea_prose  # noqa: E402
from bluewatch.config import settings  # noqa: E402
from bluewatch.i18n import I18N_DIR, pattern, walk  # noqa: E402
from bluewatch.ideas.models import IdeaSubmission  # noqa: E402
from bluewatch.ideas.nextsteps import check_title  # noqa: E402
from bluewatch.ideas.queue import (  # noqa: E402
    EVIDENCE_ORDER,
    MAX_TOP_N,
    POTENTIAL_WORDS,
    SAMPLE_PATH,
    next_in_line,
    why_these,
)
from bluewatch.ideas.rubric import CRITERIA, TIER_LABELS, strength  # noqa: E402
from bluewatch.ideas.vet import NOTES  # noqa: E402
from bluewatch.lookup import closed_message  # noqa: E402
from bluewatch.rules.alerts import deadline_reason  # noqa: E402
from bluewatch.rules.score import closed_rule  # noqa: E402
from bluewatch.sources.common import CLOSED_STATUSES  # noqa: E402

MODES = ("apelago", "redstone")
PRESETS = ("blue", "climate_circular")
FOUNDER_IDS = (("FI", "3652359-1"), ("NO", "938525420"))
SESSION = {"X-Demo-Session": "collect-strings-session"}
DAYS = 7

client = TestClient(app_module.app)
found: set[str] = set()


def keep(text: str) -> str:
    if text.strip():
        found.add(pattern(text)[0])
    return text


def collect(data: object, path: str = "") -> None:
    walk(data, keep)
    if path.startswith("/api/ideas/"):
        idea_prose(data, keep)


def get(path: str) -> object:
    response = client.get(path)
    response.raise_for_status()
    data = response.json()
    collect(data, path)
    return data


def post(path: str, body: dict | None) -> object:
    response = client.post(path, json=body, headers=SESSION)
    response.raise_for_status()
    data = response.json()
    collect(data, path)
    return data


def collect_day() -> None:
    for path in ("/api/meta", "/api/sources", "/api/presets", "/api/precision", "/api/ideas/rubric"):
        get(path)
    for country, business_id in FOUNDER_IDS:
        post("/api/founder", {"country": country, "business_id": business_id})
    for mode in MODES:
        for path in ("bridges", "funding", "alerts", "scout"):
            get(f"/api/{path}?mode={mode}")
        for preset in PRESETS:
            query = f"mode={mode}&preset={preset}"
            get(f"/api/list?{query}")
            get(f"/api/ideas/queue?{query}")
            get(f"/api/ideas/queue?{query}&sample=1")
            rows = get(f"/api/companies?{query}")
            assert isinstance(rows, list)
            for row in rows:
                get(f"/api/companies/{row['id']}?{query}")
    for preset in PRESETS:
        get(f"/api/ideas/form?preset={preset}")


def collect_outreach() -> None:
    """The sending rules' reasons and the simulated reply's confirmations, for every company that can be drafted.

    Only these parts are collected: a draft's own text keeps the language it was written in."""

    def desk(path: str, body: dict | None = None) -> dict:
        response = client.post(path, json=body, headers=SESSION)
        response.raise_for_status()
        return response.json()

    for mode in MODES:
        for row in client.get(f"/api/companies?mode={mode}&preset=blue").json():
            desk("/api/outreach/reset")
            created = client.post("/api/outreach/drafts", json={"company_id": row["id"], "mode": mode}, headers=SESSION)
            if created.status_code == 422:  # only resolved companies are drafted
                continue
            created.raise_for_status()
            view = created.json()
            draft = f"/api/outreach/drafts/{view['draft']['id']}"
            collect(view["decision"])
            collect(desk(f"{draft}/approve", {"text_hash": view["text_hash"]})["decision"])
            collect(desk(f"{draft}/send")["decision"])
            collect(desk(f"{draft}/reply")["confirmed"])


def collect_sharing() -> None:
    """One sample idea shared and withdrawn: the receipt, the shared item's origin in the queue, the withdrawal."""
    raw = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))["ideas"][0]
    submission = {key: value for key, value in raw.items() if key in IdeaSubmission.model_fields}
    form = get(f"/api/ideas/form?preset={submission['preset']}")
    assert isinstance(form, dict)
    post(
        "/api/ideas/share",
        {"submission": submission, "consent": True, "consent_text_version": form["consent_text_version"]},
    )
    for mode in MODES:
        path = f"/api/ideas/queue?mode={mode}&preset={submission['preset']}"
        response = client.get(path, headers=SESSION)
        response.raise_for_status()
        collect(response.json(), path)
    post("/api/ideas/withdraw", None)
    post("/api/ideas/withdraw", None)  # nothing left to withdraw


def main(days: int) -> None:
    # The collector reads thousands of answers in a row; the visitor rate limits would stop it.
    deps._limiter = RateLimiter(per_ip_per_hour=1_000_000, total_per_minute=1_000_000)
    first: date = settings().today
    for offset in range(days):
        os.environ["BLUEWATCH_TODAY"] = (first + timedelta(days=offset)).isoformat()
        collect_day()
    collect_outreach()
    collect_sharing()
    # A visitor's own read can carry any reader note (key, switch, budget) and any criterion as its biggest
    # gap, so those are listed whole; the note naming the model's error cannot be.
    for note in NOTES.values():
        if "{" not in note:
            keep(note)
    for criterion in CRITERIA:
        keep(check_title(criterion.label))
        # A strength quoting the team is translated without its quote (see quoted_strength), so every rung that
        # makes a strength (2 and 3; never the public trace) is listed on its own.
        for rung_label in criterion.rungs[2:] if criterion.id != "trace" else ():
            keep(strength(criterion.label, rung_label))
    # A deadline countdown can fall in any month, on any day, so every wording is listed whole.
    for month in range(1, 13):
        for days_left in (0, 1, 2):
            keep(deadline_reason(date(first.year, month, 1), days_left))
    # A live lookup can meet a company in any closed register status; no recorded one is closed.
    for status in CLOSED_STATUSES:
        keep(closed_rule(status))
        keep(closed_message(status))
    # Idea Harbour's queue summary: any Top N cut, and the first idea below it in any tier and band.
    for sample in (False, True):
        for top_n in range(1, MAX_TOP_N + 1):
            for chosen in range(top_n + 1):
                keep(why_these(chosen, MAX_TOP_N, top_n, sample=sample))
    for tier in ("bring_now", "ask_two"):
        for potential in POTENTIAL_WORDS:
            for evidence in EVIDENCE_ORDER:
                keep(next_in_line(MAX_TOP_N + 1, TIER_LABELS[tier], potential, evidence))
    out = I18N_DIR / "source.json"
    payload = {"generated_by": "scripts/collect_strings.py", "strings": sorted(found)}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: {len(found)} patterns, {first} to {first + timedelta(days=days - 1)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else DAYS)
