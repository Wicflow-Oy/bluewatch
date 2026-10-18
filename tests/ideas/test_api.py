"""The HTTP guards: nothing stored without consent, size limits, rate limits, session isolation."""

from __future__ import annotations

import json
import logging

import pytest

from bluewatch import i18n
from bluewatch.api import deps
from bluewatch.api import ideas as ideas_api
from bluewatch.api.guards import RateLimiter
from bluewatch.ideas import vet as vet_mod
from tests.ideas.helpers import OTHER_SESSION, SESSION, payload, strong_submission

MARKER = "Zebra-marker-7731 tidal kelp lantern"


def share_body(client, **changes) -> dict:
    version = client.get("/api/ideas/form").json()["consent_text_version"]
    return {"submission": payload(strong_submission(**changes)), "consent": True, "consent_text_version": version}


def test_form_lists_options_limits_and_consent(client):
    form = client.get("/api/ideas/form").json()
    assert [o["value"] for o in form["impact_areas"]][1] == "A Clean Ocean"
    assert form["limits"]["problem"] == 600 and form["model_reading"] is False
    assert "withdraw" in form["consent_text"] and "names" in form["privacy_note"]


def test_asking_for_claude_never_fails_and_says_which_reader_answered(client, monkeypatch):
    form = client.get("/api/ideas/form").json()
    assert "Anthropic's API" in form["ai_read_text"] and form["ai_read_off_note"]
    body = {**payload(strong_submission()), "ai_read": True}
    off = client.post("/api/ideas/vet", json=body).json()
    assert off["reader"] == "rules" and off["reader_note"] == vet_mod.NOTES["off"]
    monkeypatch.setenv("BLUEWATCH_IDEAS_MODEL", "1")
    no_key = client.post("/api/ideas/vet", json=body).json()
    assert no_key["reader"] == "rules" and no_key["reader_note"] == vet_mod.NOTES["no_key"]
    chose = client.post("/api/ideas/vet", json={**body, "ai_read": False}).json()
    assert chose["reader_note"] == vet_mod.NOTES["chose_rules"]


def test_rubric_is_public(client):
    body = client.get("/api/ideas/rubric").json()
    assert len(body["criteria"]) == 8 and body["anti_gaming"] and body["tier_rules"]


def test_vet_stores_and_logs_nothing(client, caplog):
    caplog.set_level(logging.DEBUG)
    r = client.post("/api/ideas/vet", json=payload(strong_submission(problem=f"{MARKER}. Farms lose 15% of feed.")))
    assert r.status_code == 200 and r.json()["stored"] is False
    assert len(ideas_api._shared) == 0
    assert all(MARKER not in record.getMessage() for record in caplog.records)
    assert r.headers["cache-control"] == "no-store" and r.headers["x-robots-tag"] == "noindex, nofollow"


def test_a_read_in_finnish_words_its_steps_and_sources_and_keeps_the_teams_words(client):
    english = client.post("/api/ideas/vet", json=payload(strong_submission())).json()
    finnish = client.post("/api/ideas/vet?lang=fi", json=payload(strong_submission())).json()

    def finnish_for(text: str) -> str:
        assert i18n.pattern(text)[0] in i18n.table("fi"), text
        return i18n.localize_text(text, "fi")

    for en, fi in zip(english["next_steps"], finnish["next_steps"], strict=True):
        if en["kind"] in ideas_api.RULE_TITLED_STEPS:
            assert fi["title"] == finnish_for(en["title"])
        if en["status"]:
            assert fi["status"] == finnish_for(en["status"])
    claims = zip(english["ledger"]["claims"], finnish["ledger"]["claims"], strict=True)
    assert all(fi["source"] == finnish_for(en["source"]) and fi["quote"] == en["quote"] for en, fi in claims)


@pytest.mark.parametrize(
    "changes",
    [
        {"problem": "x" * 601},
        {"title": "ab"},
        {"links": ["https://a.org", "https://b.org", "https://c.org", "https://d.org"]},
        {"links": ["javascript:alert(1)"]},
        {"team": [{"role": "build"}] * 7},
        {"impact_area": "Mars"},
        {"email": "someone@example.org"},  # the form has no contact fields, and extra fields are refused
        {"exists": ["unicorn"]},
    ],
)
def test_field_limits(client, changes):
    body = {**payload(strong_submission()), **changes}
    assert client.post("/api/ideas/vet", json=body).status_code == 422


def test_body_size_limit(client):
    r = client.post(
        "/api/ideas/vet", content=json.dumps({"title": "x" * 20_000}), headers={"content-type": "application/json"}
    )
    assert r.status_code == 413


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1, total_per_minute=100))
    assert client.post("/api/ideas/vet", json=payload(strong_submission())).status_code == 200
    r = client.post("/api/ideas/vet", json=payload(strong_submission()))
    assert r.status_code == 429 and "idea checks" in r.json()["detail"]


def test_idea_checks_and_lookups_share_one_hourly_budget(client, monkeypatch):
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1, total_per_minute=100))
    assert client.post("/api/ideas/vet", json=payload(strong_submission())).status_code == 200
    r = client.post("/api/lookup", json={"country": "FI", "business_id": "3652359-1"})
    assert r.status_code == 429


def test_share_needs_consent_and_a_session(client):
    body = share_body(client)
    assert client.post("/api/ideas/share", json=body).status_code == 422  # no session header
    assert client.post("/api/ideas/share", json=body, headers={"X-Demo-Session": "short"}).status_code == 422
    no = {**body, "consent": False}
    assert client.post("/api/ideas/share", json=no, headers={"X-Demo-Session": SESSION}).status_code == 422
    old = {**body, "consent_text_version": "v0"}
    assert client.post("/api/ideas/share", json=old, headers={"X-Demo-Session": SESSION}).status_code == 409
    assert len(ideas_api._shared) == 0


def test_shared_idea_is_visible_to_its_own_session_only_and_can_be_withdrawn(client):
    r = client.post("/api/ideas/share", json=share_body(client), headers={"X-Demo-Session": SESSION})
    receipt = r.json()
    assert r.status_code == 200 and receipt["demo"] is True and receipt["stored"] == "session_memory"
    assert receipt["consent"]["given"] is True and receipt["expires_at"]

    mine = client.get("/api/ideas/queue", headers={"X-Demo-Session": SESSION}).json()
    assert mine["session_items"] == 1 and mine["items"][0]["id"] == receipt["item_id"]
    assert mine["items"][0]["assessment"]["stored"] is True
    for other in ({"X-Demo-Session": OTHER_SESSION}, {}):
        queue = client.get("/api/ideas/queue", headers=other).json()
        assert queue["session_items"] == 0 and all(i["origin"]["kind"] != "your_submission" for i in queue["items"])

    gone = client.post("/api/ideas/withdraw", headers={"X-Demo-Session": SESSION}).json()
    assert gone["removed"] == 1
    assert client.get("/api/ideas/queue", headers={"X-Demo-Session": SESSION}).json()["session_items"] == 0


DELIVERY_CLAIMS = ("shared with a'pelago", "a'pelago's review queue", "a'pelago receives", "reviewers can now see")


def test_sharing_says_it_is_simulated_and_never_claims_delivery(client):
    """Nothing reaches A'Pelago from this prototype, so no text the team reads may say it did."""
    consent = client.get("/api/ideas/form").json()["consent_text"]
    receipt = client.post("/api/ideas/share", json=share_body(client), headers={"X-Demo-Session": SESSION}).json()
    gone = client.post("/api/ideas/withdraw", headers={"X-Demo-Session": SESSION}).json()
    none = client.post("/api/ideas/withdraw", headers={"X-Demo-Session": SESSION}).json()
    assert "simulated" in consent and "A'Pelago does not receive it" in consent
    assert "simulated" in receipt["message"] and "not sent to A'Pelago" in receipt["message"]
    assert "60 minutes" in receipt["message"]
    assert "demo review queue" in gone["message"] and "demo review queue" in none["message"]
    for text in (consent, receipt["message"], gone["message"], none["message"]):
        assert not any(claim in text.lower() for claim in DELIVERY_CLAIMS), text


@pytest.mark.parametrize(("lang", "word"), [("fi", "simuloitu"), ("sv", "simulerad")])
def test_the_simulated_share_is_said_in_finnish_and_swedish_too(client, lang, word):
    form = client.get(f"/api/ideas/form?lang={lang}").json()
    body = {**share_body(client), "consent_text_version": form["consent_text_version"]}
    receipt = client.post(f"/api/ideas/share?lang={lang}", json=body, headers={"X-Demo-Session": SESSION}).json()
    assert word in form["consent_text"] and word in receipt["message"]
    assert "A'Pelago" in receipt["message"] and "60" in receipt["message"]


def test_real_storage_receipt_still_says_nothing_went_to_apelago(client, monkeypatch, tmp_path):
    monkeypatch.setenv("BLUEWATCH_IDEAS_PERSIST", "1")
    monkeypatch.setenv("BLUEWATCH_IDEAS_PERSIST_PATH", str(tmp_path / "shared.jsonl"))
    monkeypatch.setenv("BLUEWATCH_PUBLIC", "0")
    receipt = client.post("/api/ideas/share", json=share_body(client), headers={"X-Demo-Session": SESSION}).json()
    assert receipt["stored"] == "file" and "not sent to A'Pelago" in receipt["message"]


def test_a_reloaded_page_learns_what_its_session_shared_so_it_can_withdraw(client):
    """After a reload the student page lost its receipt and Withdraw while the idea stayed shared."""
    mine, other = {"X-Demo-Session": SESSION}, {"X-Demo-Session": OTHER_SESSION}
    assert client.get("/api/ideas/shared", headers=mine).json() == {"count": 0, "expires_at": None}
    client.post("/api/ideas/share", json=share_body(client), headers=mine)
    shared = client.get("/api/ideas/shared", headers=mine).json()
    assert shared["count"] == 1 and shared["expires_at"]
    assert client.get("/api/ideas/shared", headers=other).json()["count"] == 0
    assert client.get("/api/ideas/shared").status_code == 422  # no session, nothing to tell
    client.post("/api/ideas/withdraw", headers=mine)
    assert client.get("/api/ideas/shared", headers=mine).json()["count"] == 0


def test_share_reads_the_idea_again_and_accepts_no_tier_from_the_browser(client):
    body = share_body(client)
    body["submission"] = {"title": "Ocean app", "problem": "Plastic is bad", "solution": "An app"}
    forged = {**body, "tier": "bring_now"}
    assert client.post("/api/ideas/share", json=forged, headers={"X-Demo-Session": SESSION}).status_code == 422
    assert client.post("/api/ideas/share", json=body, headers={"X-Demo-Session": SESSION}).status_code == 200
    items = client.get("/api/ideas/queue", headers={"X-Demo-Session": SESSION}).json()["items"]
    mine = next(i for i in items if i["origin"]["kind"] == "your_submission")
    assert mine["assessment"]["tier"] == "not_yet" and mine["in_top"] is False


def test_real_storage_is_off_by_default_and_never_in_public_mode(client, monkeypatch, tmp_path):
    target = tmp_path / "shared.jsonl"
    monkeypatch.setenv("BLUEWATCH_IDEAS_PERSIST_PATH", str(target))
    client.post("/api/ideas/share", json=share_body(client), headers={"X-Demo-Session": SESSION})
    assert not target.exists()

    monkeypatch.setenv("BLUEWATCH_IDEAS_PERSIST", "1")
    monkeypatch.setenv("BLUEWATCH_PUBLIC", "1")
    client.post("/api/ideas/share", json=share_body(client), headers={"X-Demo-Session": SESSION})
    assert not target.exists()

    monkeypatch.setenv("BLUEWATCH_PUBLIC", "0")
    receipt = client.post("/api/ideas/share", json=share_body(client), headers={"X-Demo-Session": SESSION}).json()
    assert receipt["stored"] == "file" and receipt["demo"] is False
    line = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert line["consent"]["given"] is True and line["submission"]["title"] == "FeedSense for fish farms"


def test_queue_parameters_are_validated(client):
    assert client.get("/api/ideas/queue?mode=other").status_code == 422
    assert client.get("/api/ideas/queue?top_n=50").status_code == 422
    assert client.get("/api/ideas/queue?preset=climate_circular&mode=redstone").status_code == 200
    unknown = client.get("/api/ideas/form?preset=green")
    assert unknown.status_code == 422 and "Available: blue, climate_circular" in unknown.json()["detail"]


def test_sharing_an_edited_idea_again_replaces_the_first_share(client):
    headers = {"X-Demo-Session": SESSION}
    first = client.post("/api/ideas/share", json=share_body(client), headers=headers).json()
    edited = share_body(client, who_pays="Farms pay a subscription per site, about 350 EUR a month.")
    second = client.post("/api/ideas/share", json=edited, headers=headers).json()
    assert first["item_id"] != second["item_id"]
    mine = [
        i["id"]
        for i in client.get("/api/ideas/queue", headers=headers).json()["items"]
        if i["origin"]["kind"] == "your_submission"
    ]
    assert mine == [second["item_id"]]
    other = share_body(
        client,
        title="Ballast water sampler",
        problem="Ports cannot check ballast water fast.",
        who_has_it="Port state control officers.",
        solution="A handheld sampler with a sensor.",
    )
    client.post("/api/ideas/share", json=other, headers=headers)
    assert client.get("/api/ideas/queue", headers=headers).json()["session_items"] == 2


def test_the_sample_preview_is_a_separate_labelled_queue(client):
    headers = {"X-Demo-Session": SESSION}
    client.post("/api/ideas/share", json=share_body(client), headers=headers)
    sample = client.get("/api/ideas/queue?sample=1", headers=headers).json()
    assert sample["sample"] is True and sample["sample_label"].startswith("Sample data: invented")
    assert sample["items"] and all(i["id"].startswith("sample:") for i in sample["items"])
    assert all(i["origin"]["label"] == "Sample submission (invented)" for i in sample["items"])
    assert sample["session_items"] == 0 and sample["items"][0]["assessment"]["reader"] == "rules"
    live = client.get("/api/ideas/queue", headers=headers).json()
    assert live["sample"] is False and live["sample_label"] is None
    assert not [i for i in live["items"] if i["id"].startswith("sample:")]


def test_sample_duplicates_are_flagged_like_live_ones(client):
    items = client.get("/api/ideas/queue?sample=1").json()["items"]
    twins = {i["id"]: i["duplicate_of"] for i in items if i["duplicate_of"]}
    assert {"sample:S19", "sample:S34", "sample:S47"} <= set(twins)


def test_invite_notes_speak_as_the_product_never_as_a_demo(client):
    """Invitations are product text; only the share receipt says the sharing is simulated (see above)."""
    invites = [i["invite"]["note"] for i in client.get("/api/ideas/queue").json()["items"] if i["invite"]]
    assert invites
    for text in invites:
        assert "demo" not in text.lower()
