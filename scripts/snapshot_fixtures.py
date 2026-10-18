"""Snapshot the real API output into frontend/src/fixtures/*.json: the UI's fallback when the API is down.

Every fixture is what the API serves offline from the verified demo pack and recorded register data,
so the fallback never shows a number the rules did not compute. Run from the repo root after any rules
or data change:

    .venv/bin/python scripts/snapshot_fixtures.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Offline and reproducible: recorded data only, no keys, no live lookups.
os.environ.update({"BLUEWATCH_SKIP_ENV_LOCAL": "1", "BLUEWATCH_OFFLINE": "1", "BLUEWATCH_LIVE_LOOKUPS": "0"})
os.environ.pop("ANTHROPIC_API_KEY", None)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from bluewatch.api.app import app  # noqa: E402

OUT = ROOT / "frontend" / "src" / "fixtures"
MODES = ("apelago", "redstone")
PRESETS = ("blue", "climate_circular")
# The founder-view demo pair: SBEP call 4 flips between them.
FOUNDER_IDS = (("FI", "3652359-1"), ("NO", "938525420"))

client = TestClient(app)


def get(path: str):
    response = client.get(path)
    response.raise_for_status()
    return response.json()


def post(path: str, body: dict):
    response = client.post(path, json=body)
    response.raise_for_status()
    return response.json()


def write(name: str, data) -> None:
    payload = {
        "generated_by": "scripts/snapshot_fixtures.py",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data": data,
    }
    (OUT / f"{name}.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    write("meta", get("/api/meta"))
    write("presets", get("/api/presets"))
    write("precision", get("/api/precision"))
    write(
        "founder",
        {
            f"{country}:{bid}": post("/api/founder", {"country": country, "business_id": bid})
            for country, bid in FOUNDER_IDS
        },
    )
    for mode in MODES:
        write(f"bridges.{mode}", get(f"/api/bridges?mode={mode}"))
        write(f"funding.{mode}", get(f"/api/funding?mode={mode}"))
        write(f"alerts.{mode}", get(f"/api/alerts?mode={mode}"))
        write(f"scout.{mode}", get(f"/api/scout?mode={mode}"))
        for preset in PRESETS:
            query = f"mode={mode}&preset={preset}"
            short = get(f"/api/list?{query}")
            write(f"list.{mode}.{preset}", short)
            write(f"companies.{mode}.{preset}", get(f"/api/companies?{query}"))
            # Cards for the listed companies only: every card would be megabytes for a fallback.
            write(
                f"cards.{mode}.{preset}",
                {e["company_id"]: get(f"/api/companies/{e['company_id']}?{query}") for e in short["entries"]},
            )
    for path in sorted(OUT.glob("*.json")):
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
