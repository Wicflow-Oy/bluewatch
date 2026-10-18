"""What /api/scout serves to the browser: plans with their public project, and nothing internal."""

from fastapi.testclient import TestClient

from bluewatch.api.app import app

client = TestClient(app)


def test_each_plan_carries_its_public_project():
    plans = client.get("/api/scout").json()
    assert plans and all(p["project"]["id"] == p["project_id"] for p in plans)
    ku_exe = plans[0]["project"]
    assert ku_exe["team_or_project"] == "KU.exe" and ku_exe["event"] == "PORTATHON 2026"
    assert ku_exe["placement"] == "1st" and ku_exe["year"] == 2026
    assert ku_exe["source_url"].startswith("https://kmtp.lt/")


def test_the_workspace_decides_the_offer():
    offers = {mode: client.get(f"/api/scout?mode={mode}").json()[0]["offer"] for mode in ("apelago", "redstone")}
    assert "Northern Blue" in offers["apelago"] and "Redstone" in offers["redstone"]
    assert client.get("/api/scout?mode=elsewhere").status_code == 422


def test_internal_research_notes_never_reach_the_browser():
    body = client.get("/api/scout?top_n=200").text
    assert '"meta"' not in body and '"verified"' not in body and "plan_id" not in body


def test_youth_events_are_never_served():
    events = [p["project"]["event"] for p in client.get("/api/scout?top_n=200").json()]
    assert not any("youth" in e.lower() or "school" in e.lower() for e in events)
