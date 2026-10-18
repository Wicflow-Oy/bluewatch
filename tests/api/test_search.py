from fastapi.testclient import TestClient

from bluewatch.api import app as app_module
from bluewatch.api import deps
from bluewatch.api.guards import RateLimiter

client = TestClient(app_module.app)


def test_search_by_name_offline():
    r = client.post("/api/search", json={"query": "havnio"})
    assert r.status_code == 200
    body = r.json()
    assert body["candidates"][0]["business_id"] == "938525420"
    assert body["candidates"][0]["company_id"] == "NO:938525420"
    assert {s["state"] for s in body["sources"]} == {"cached"}


def test_search_rejects_short_queries_and_unknown_countries():
    assert client.post("/api/search", json={"query": "ab"}).status_code == 422
    assert client.post("/api/search", json={"query": "havnio", "country": "SE"}).status_code == 422


def test_search_is_rate_limited(monkeypatch):
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1, total_per_minute=100))
    assert client.post("/api/search", json={"query": "havnio"}).status_code == 200
    r = client.post("/api/search", json={"query": "havnio"})
    assert r.status_code == 429 and "limit" in r.json()["detail"].lower()
