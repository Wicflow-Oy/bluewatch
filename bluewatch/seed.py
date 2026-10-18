"""Read-only access to the verified demo pack (copied into data/seed/) and recorded fixtures."""

from __future__ import annotations

import json
from functools import lru_cache

from bluewatch.config import FIXTURES_DIR, SEED_DIR

SEED_FILES = {
    "startups": "startups.json",
    "investors": "investors.json",
    "grants": "grants.json",
    "partners": "partners.json",
    "bridges": "bridges_seed.json",
    "hackathon_projects": "hackathon_projects_seed.json",
    "hackathon_scout": "hackathon_scout_seed.json",
    "research_prestartup": "research_prestartup.json",
    "answer_keys": "answer_keys.json",
    "signals_cache": "signals_cache.json",
    "demo_list_2026_10_12": "monday10_demo_2026-10-12.json",
}


@lru_cache(maxsize=None)
def load(name: str):
    """Load a seed file by short name (see SEED_FILES)."""
    return json.loads((SEED_DIR / SEED_FILES[name]).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def fixture(relative: str):
    """Load a recorded fixture, e.g. fixture('sources/ted_open_tenders_blue_nordic_baltic.json')."""
    return json.loads((FIXTURES_DIR / relative).read_text(encoding="utf-8"))
