"""rules_version: one hash over the rules code and the presets, stamped on every assessment and list,
so a result can always be traced to the exact rules that produced it."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from bluewatch.rules.presets import PRESETS_DIR

RULES_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def rules_version() -> str:
    digest = hashlib.sha256()
    files = sorted(RULES_DIR.glob("*.py")) + sorted(PRESETS_DIR.glob("*.json"))
    for path in files:
        digest.update(path.name.encode("utf-8"))
        # Normalise line endings so the hash is the same on Windows and Linux checkouts.
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return f"rules-{digest.hexdigest()[:12]}"
