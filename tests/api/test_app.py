from fastapi.testclient import TestClient

from bluewatch.api.app import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"ok": True}


def test_meta_has_names_and_no_keys():
    body = client.get("/api/meta").json()
    assert body["product_name"]
    assert body["list_name"]
    assert body["outreach_mode"] == "demo"
    text = str(body).lower()
    assert "api_key" not in text and "password" not in text


def test_meta_names_the_deployed_build(monkeypatch):
    monkeypatch.delenv("BLUEWATCH_BUILD", raising=False)
    assert client.get("/api/meta").json()["build"] == "dev"
    monkeypatch.setenv("BLUEWATCH_BUILD", "7aaf76f")
    assert client.get("/api/meta?lang=fi").json()["build"] == "7aaf76f"


def test_sources_never_claim_live_in_demo():
    states = {s["state"] for s in client.get("/api/sources").json()}
    assert "live" not in states  # the offline demo serves recorded snapshots and must say so
