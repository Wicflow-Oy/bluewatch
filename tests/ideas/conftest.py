from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bluewatch.api import deps
from bluewatch.api import ideas as ideas_api
from bluewatch.api.app import app
from bluewatch.api.guards import RateLimiter
from bluewatch.ideas.store import SharedIdeas


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """The real app, with a fresh shared-ideas store and a generous rate limit for each test."""
    monkeypatch.setattr(ideas_api, "_shared", SharedIdeas())
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1000, total_per_minute=1000))
    monkeypatch.delenv("BLUEWATCH_IDEAS_MODEL", raising=False)
    monkeypatch.delenv("BLUEWATCH_IDEAS_PERSIST", raising=False)
    return TestClient(app)
