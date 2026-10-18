import threading

from fastapi.testclient import TestClient

from bluewatch.api import app as app_module
from bluewatch.api import deps
from bluewatch.api.guards import RateLimiter

client = TestClient(app_module.app)


def test_noindex_and_security_headers():
    r = client.get("/api/health")
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["cache-control"] == "no-store"
    assert client.get("/robots.txt").text == "User-agent: *\nDisallow: /\n"


def test_lookup_validates_ids():
    r = client.post("/api/lookup", json={"country": "FI", "business_id": "12-34"})
    assert r.status_code == 422
    r = client.post("/api/lookup", json={"country": "SE", "business_id": "5560000000"})
    assert r.status_code == 422


def test_lookup_without_live_mode_says_so():
    r = client.post("/api/lookup", json={"country": "NO", "business_id": "938525420"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"]["state"] == "cached"
    assert "off" in body["status"]["detail"].lower()
    assert body["recorded_only"] is True


def test_an_id_missing_from_the_recorded_data_reads_as_a_setting_not_an_outage():
    body = client.post("/api/lookup?lang=fi", json={"country": "NO", "business_id": "923609016"}).json()
    assert body["recorded_only"] is True and not body["found"]
    assert body["message"].startswith("Reaaliaikaiset rekisterihaut ovat pois päältä")
    assert "live lookups" not in body["status"]["detail"]  # the register's reason is in Finnish too


def test_lookup_rate_limited(monkeypatch):
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1, total_per_minute=100))
    assert client.post("/api/lookup", json={"country": "NO", "business_id": "938525420"}).status_code == 200
    assert client.post("/api/lookup", json={"country": "NO", "business_id": "938525420"}).status_code == 429


def test_founder_share_is_demo_only():
    body = client.post("/api/founder/share").json()
    assert body["demo"] is True and body["stored"] is False


def test_health_answers_while_the_caches_warm(monkeypatch):
    warming = threading.Event()
    release = threading.Event()
    monkeypatch.setattr(app_module.demo, "warm", lambda: (warming.set(), release.wait(5)))
    with TestClient(app_module.app) as started:
        assert warming.wait(5)
        assert started.get("/api/health").json() == {"ok": True}
        release.set()
