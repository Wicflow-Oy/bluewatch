"""The screen routes: companies, presets, bridges, funding, alerts, precision, the live card and the desk."""

from __future__ import annotations

import asyncio
import re

import pytest
from fastapi.testclient import TestClient

from bluewatch import i18n
from bluewatch.api import app as app_module
from bluewatch.api import deps
from bluewatch.api.app import app
from bluewatch.api.guards import RateLimiter
from bluewatch.api.sessions import DeskSessions

client = TestClient(app)
MERIVA, HAVNIO, ALPO = "FI:3652359-1", "NO:938525420", "FI:3101791-3"
SESSION = {"X-Demo-Session": "test-session-aaaaaaaaaaaa"}


@pytest.fixture(autouse=True)
def fresh_guards(monkeypatch):
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1000, total_per_minute=1000))
    monkeypatch.setattr(app_module, "_desks", DeskSessions())


@pytest.mark.parametrize("mode", ["apelago", "redstone"])
def test_companies_lists_the_whole_set_with_first_steps(mode):
    rows = client.get(f"/api/companies?mode={mode}").json()
    assert len(rows) > 100 and len({r["id"] for r in rows}) == len(rows)
    alpo = next(r for r in rows if r["id"] == ALPO)
    assert alpo["registry_id"] == "3101791-3" and alpo["next_action"] and alpo["deadline"]
    assert all(0 <= r["potential"] <= 1 and 0 <= r["evidence"] <= 1 for r in rows)


def test_presets_and_the_second_preset_reranks_the_same_companies():
    names = [p["name"] for p in client.get("/api/presets").json()]
    assert names == ["blue", "climate_circular"]
    blue = client.get("/api/companies?preset=blue").json()
    climate = client.get("/api/companies?preset=climate_circular").json()
    assert {r["id"] for r in blue} == {r["id"] for r in climate}
    assert [r["id"] for r in blue][:10] != [r["id"] for r in climate][:10]
    assert client.get("/api/list?preset=climate_circular").json()["preset"] == "climate_circular"
    assert (
        client.get(f"/api/companies/{ALPO}?preset=climate_circular").json()["assessment"]["preset"]
        == "climate_circular"
    )


def test_unknown_preset_is_refused():
    assert client.get("/api/list?preset=nope").status_code == 422
    assert client.get("/api/companies?preset=nope").status_code == 422


@pytest.mark.parametrize("mode", ["apelago", "redstone"])
def test_bridges_are_ranked_with_b1_first_and_an_anonymised_label(mode):
    bridges = client.get(f"/api/bridges?mode={mode}").json()
    assert bridges[0]["id"] == "B1"
    assert bridges[0]["anonymised_name"] == "A Rauma boat builder"
    assert all(b["anonymised_name"] and b["rank_parts"]["score"] >= 0 for b in bridges)
    assert all(b["mode"] in (mode, "both") for b in bridges)
    scores = [b["rank_parts"]["score"] for b in bridges]
    assert scores == sorted(scores, reverse=True)


def test_one_bridge_by_id_seeded_or_generated():
    b1 = client.get("/api/bridges/B1").json()
    assert b1["company"]["name"] == "Alpo Pro Boats" and b1["counterparty"]["name"] == "Sansia Oy"
    assert b1["deadline"] == "2026-10-30" and b1["evidence_company"] and b1["evidence_counterparty"]
    generated = next(b for b in client.get("/api/bridges").json() if b["generator"] != "seed")
    assert client.get(f"/api/bridges/{generated['id']}").json()["id"] == generated["id"]
    assert client.get("/api/bridges/nope").status_code == 404


@pytest.mark.parametrize("mode", ["apelago", "redstone"])
def test_funding_shows_the_sbep_country_flip_with_its_rule(mode):
    catalogue = client.get(f"/api/funding?mode={mode}").json()
    assert MERIVA in catalogue["company_ids"] and HAVNIO in catalogue["company_ids"]
    sbep = next(i for i in catalogue["instruments"] if i["id"] == "sbep-jtc4")
    tiers = {t["company_id"]: t for t in sbep["tiers"]}
    assert tiers[MERIVA]["tier"] == "excluded" and "Finnish funder" in tiers[MERIVA]["deciding_rule"]
    assert tiers[HAVNIO]["tier"] == "possible"
    country = next(r for r in sbep["rules"] if r["field"] == "country_rule")
    assert country["verified"] and country["source_tag"] == "read"
    assert sbep["url"] and sbep["deadline"] == "2026-11-16"


def test_certain_needs_every_check_read_on_the_official_page():
    for mode in ("apelago", "redstone"):
        for inst in client.get(f"/api/funding?mode={mode}").json()["instruments"]:
            for tier in inst["tiers"]:
                if tier["tier"] == "certain":
                    assert tier["rule_verified"] and all(c["verified"] for c in tier["checks"])


def test_alerts_are_within_30_days_and_apelago_hides_share_issues():
    for mode in ("apelago", "redstone"):
        alerts = client.get(f"/api/alerts?mode={mode}").json()
        assert alerts
        for alert in alerts:
            if alert["trigger"].startswith("deadline"):
                assert alert["deadline"] and alert["trigger"] in ("deadline_14d", "deadline_30d")
    assert not any(a["trigger"] == "new_share_issue" for a in client.get("/api/alerts?mode=apelago").json())


def test_precision_puts_the_age_baseline_beside_every_scored_number():
    report = client.get("/api/precision").json()
    scored = [lv for lv in report["levels"] if lv["n"] > 0]
    assert scored and all(lv["baseline_exact"] is not None for lv in scored)
    assert report["rules_hash"] and len(report["traps"]) == 10
    passed = sum(t["passed"] for t in report["traps"])
    assert f"Entity traps: {passed} of 10 passed." in report["notes"]  # shown as computed, never rounded up
    assert any("baseline" in note.lower() for note in report["notes"])


BLIND_CSV = "company,id,country,trl,brl,stage\nMeriva Oy,3652359-1,FI,,2,pre-seed\nHAVNIO AS,938525420,NO,,,seed\n"


def test_blind_upload_is_scored_in_memory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = client.post("/api/precision/blind", content=BLIND_CSV, headers={"Content-Type": "text/csv"})
    report = response.json()
    assert response.status_code == 200 and report["blind"] is True
    assert any("Meriva Oy" in note for note in report["notes"])
    assert list(tmp_path.iterdir()) == []  # nothing written


def test_blind_upload_is_size_capped_and_validated():
    big = "company\n" + "x" * 210_000
    assert client.post("/api/precision/blind", content=big, headers={"Content-Type": "text/csv"}).status_code == 413
    bad = client.post("/api/precision/blind", content=b"\xff\xfe\x00", headers={"Content-Type": "text/csv"})
    assert bad.status_code == 422


CHUNK = b"x" * 65_536


def post_streamed(path: str, chunks: int, headers: list[tuple[bytes, bytes]]) -> tuple[int, int]:
    """POST `chunks` 64 KB chunks straight through the ASGI app, as a server would hand over a chunked or
    oversized body. Returns the status and how many chunks the app pulled; pulling them all is a failure."""
    pulled = 0

    async def receive() -> dict:
        nonlocal pulled
        if pulled >= chunks:
            raise AssertionError("the whole oversized body was read")
        pulled += 1
        return {"type": "http.request", "body": CHUNK, "more_body": True}

    sent: list[dict] = []

    async def send(message: dict) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver"), *headers],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    return next(m["status"] for m in sent if m["type"] == "http.response.start"), pulled


def test_blind_upload_without_a_length_is_refused_while_it_streams():
    """No Content-Length (chunked): the 200 KB cap stops the read after four chunks, not after 3 MB."""
    status, pulled = post_streamed("/api/precision/blind", 48, [(b"content-type", b"text/csv")])
    assert status == 413 and pulled == 4  # 4 x 64 KB is the first total over 200 KB


def test_blind_upload_with_a_large_declared_length_is_refused_before_reading():
    status, pulled = post_streamed(
        "/api/precision/blind", 48, [(b"content-type", b"text/csv"), (b"content-length", b"3145728")]
    )
    assert (status, pulled) == (413, 0)


def test_idea_form_body_is_capped_while_it_streams_even_under_a_small_declared_length():
    """A declared 15 KB that keeps coming: the ideas routes stop at their 16 KB cap all the same."""
    headers = [(b"content-type", b"application/json"), (b"content-length", b"15000")]
    status, pulled = post_streamed("/api/ideas/vet", 48, headers)
    assert (status, pulled) == (413, 1)


def test_blind_upload_is_rate_limited(monkeypatch):
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1, total_per_minute=100))
    first = client.post("/api/precision/blind", content=BLIND_CSV, headers={"Content-Type": "text/csv"})
    second = client.post("/api/precision/blind", content=BLIND_CSV, headers={"Content-Type": "text/csv"})
    assert (first.status_code, second.status_code) == (200, 429)


def test_live_card_for_a_precomputed_and_a_register_only_company():
    precomputed = client.post("/api/lookup/card", json={"country": "FI", "business_id": "3652359-1"}).json()
    assert precomputed["card"]["company"]["id"] == MERIVA
    rows = client.get("/api/companies").json()
    known = {r["id"] for r in rows}
    from bluewatch.sources import prh

    outside = next(r for r in prh._recorded_index().values() if f"FI:{r.id}" not in known and not r.natural_person)
    result = client.post("/api/lookup/card", json={"country": "FI", "business_id": outside.id}).json()
    card = result["card"]
    assert result["lookup"]["company_id"] is None and card["company"]["id"] == f"FI:{outside.id}"
    assert card["ledger"]["unknowns"]  # what the register does not say stays unknown
    assert client.post("/api/lookup/card", json={"country": "FI", "business_id": "123"}).status_code == 422


def test_live_card_shows_nothing_for_a_sole_trader(monkeypatch):
    from bluewatch import lookup
    from bluewatch.models import SourceStatus

    sole = lookup.LookupResult(
        country="FI",
        business_id="1234567-8",
        found=True,
        natural_person=True,
        status=SourceStatus(source="prh", label="PRH", state="cached"),
    )
    monkeypatch.setattr(lookup, "lookup", lambda country, raw: sole)
    result = client.post("/api/lookup/card", json={"country": "FI", "business_id": "1234567-8"}).json()
    assert result["card"] is None and result["lookup"]["registry"] is None


def _create(company_id: str = MERIVA, headers: dict = SESSION) -> dict:
    response = client.post("/api/outreach/drafts", json={"company_id": company_id}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_desk_loop_approve_demo_send_and_simulated_reply():
    view = _create()
    draft_id = view["draft"]["id"]
    assert view["draft"]["status"] == "pending_approval" and len(view["draft"]["questions"]) == 2
    refused = client.post(f"/api/outreach/drafts/{draft_id}/approve", json={"text_hash": "0" * 64}, headers=SESSION)
    assert refused.status_code == 409
    approved = client.post(
        f"/api/outreach/drafts/{draft_id}/approve", json={"text_hash": view["text_hash"]}, headers=SESSION
    ).json()
    assert approved["draft"]["status"] == "approved"
    sent = client.post(f"/api/outreach/drafts/{draft_id}/send", headers=SESSION).json()
    assert sent["draft"]["status"] == "blocked_demo"  # the public demo never sends
    reply = client.post(f"/api/outreach/drafts/{draft_id}/reply", headers=SESSION).json()
    asked = [q["evidence_id"] for q in view["draft"]["questions"]]
    assert [e["id"] for e in reply["confirmed"]] == asked
    assert all(e["state"] == "fact" and e["confirmed_by"]["by"] == "company_reply" for e in reply["confirmed"])
    assert reply["draft"]["draft"]["status"] == "replied"
    audit = client.get(f"/api/outreach/drafts/{draft_id}/audit", headers=SESSION).json()
    assert [e["action"] for e in audit] == ["submitted", "approval_refused", "approved", "public_demo", "reply_answer"]


def test_a_draft_started_from_a_bridge_is_about_that_bridge():
    for bridge_id, counterparty in [("B1", "Sansia Oy"), ("B2", "Hansel Oy")]:
        response = client.post(
            "/api/outreach/drafts", json={"company_id": ALPO, "bridge_id": bridge_id}, headers=SESSION
        )
        draft = response.json()["draft"]
        assert draft["bridge_id"] == bridge_id and counterparty in draft["subject"] and counterparty in draft["body"]
    gone = client.post("/api/outreach/drafts", json={"company_id": ALPO, "bridge_id": "B9"}, headers=SESSION)
    assert gone.status_code == 422  # never a draft about another bridge instead


def test_a_simulated_reply_says_what_the_company_confirmed():
    view = _create()
    draft_id = view["draft"]["id"]
    client.post(f"/api/outreach/drafts/{draft_id}/approve", json={"text_hash": view["text_hash"]}, headers=SESSION)
    client.post(f"/api/outreach/drafts/{draft_id}/send", headers=SESSION)
    confirmed = client.post(f"/api/outreach/drafts/{draft_id}/reply", headers=SESSION).json()["confirmed"]
    claims = [e["claim"] for e in confirmed]
    assert len(set(claims)) == len(claims) == 2
    assert all(c.startswith("Simulated reply: ") and len(c) > len("Simulated reply: ") + 10 for c in claims)
    finnish = client.post(f"/api/outreach/drafts/{draft_id}/reply?lang=fi", headers=SESSION).json()["confirmed"]
    assert all(e["claim"].startswith("Simuloitu vastaus: ") for e in finnish)


@pytest.mark.parametrize(("mode", "org"), [("apelago", "A'Pelago"), ("redstone", "Redstone")])
def test_a_draft_comes_from_the_workspace_and_shows_no_placeholder_sender(mode, org):
    response = client.post("/api/outreach/drafts", json={"company_id": MERIVA, "mode": mode}, headers=SESSION)
    view = response.json()
    body = view["draft"]["body"]
    assert body.split("\n\n")[1].startswith(f"We are {org}.") and f"Sender: {org}." in body
    assert "marketing" not in body and "DEMO-" not in body and ".invalid" not in body
    assert view["decision"]["allowed"]


def test_desk_gives_the_sending_rules_in_the_readers_language_and_the_draft_in_its_own():
    view = _create()
    draft_id = view["draft"]["id"]
    finnish = client.get(f"/api/outreach/drafts/{draft_id}?lang=fi", headers=SESSION).json()
    english = view["decision"]["reasons"]
    assert english and all(i18n.pattern(reason)[0] in i18n.table("fi") for reason in english)
    assert finnish["decision"]["reasons"] == [i18n.localize_text(reason, "fi") for reason in english]
    assert finnish["text_hash"] == view["text_hash"]
    assert {**finnish["draft"], "audit": []} == {**view["draft"], "audit": []}  # the message keeps its language
    submitted = client.get(f"/api/outreach/drafts/{draft_id}/audit?lang=fi", headers=SESSION).json()[0]
    route, *reasons = submitted["detail"].split("; ")
    assert route.startswith("route ") and reasons == finnish["decision"]["reasons"]
    assert next(e for e in finnish["draft"]["audit"] if e["action"] == "submitted")["detail"] == submitted["detail"]


def test_desk_never_calls_a_sender(monkeypatch):
    from bluewatch.api import sessions

    def explode(self, message):
        raise AssertionError("the demo desk must never send")

    monkeypatch.setattr(sessions.NeverSends, "send", explode)
    view = _create()
    draft_id = view["draft"]["id"]
    client.post(f"/api/outreach/drafts/{draft_id}/approve", json={"text_hash": view["text_hash"]}, headers=SESSION)
    assert (
        client.post(f"/api/outreach/drafts/{draft_id}/send", headers=SESSION).json()["draft"]["status"]
        == "blocked_demo"
    )


def test_desk_state_is_per_visitor_and_resettable():
    _create()
    other = {"X-Demo-Session": "test-session-bbbbbbbbbbbb"}
    assert client.get("/api/outreach/drafts", headers=other).json() == []
    assert len(client.get("/api/outreach/drafts", headers=SESSION).json()) == 1
    assert client.post("/api/outreach/reset", headers=SESSION).json() == {"reset": True}
    assert client.get("/api/outreach/drafts", headers=SESSION).json() == []


def test_desk_needs_a_valid_session_and_a_known_company():
    assert client.get("/api/outreach/drafts").status_code == 422
    assert client.get("/api/outreach/drafts", headers={"X-Demo-Session": "short"}).status_code == 422
    assert client.post("/api/outreach/drafts", json={"company_id": "FI:0000000-0"}, headers=SESSION).status_code == 404
    assert client.get("/api/outreach/drafts/od-missing", headers=SESSION).status_code == 409


def test_sessions_expire_and_are_capped():
    now = [0.0]
    desks = DeskSessions(ttl_s=10, cap=2, clock=lambda: now[0])
    first = desks.desk("session-aaaaaaaaaaaaaaaa")
    assert desks.desk("session-aaaaaaaaaaaaaaaa") is first
    desks.desk("session-bbbbbbbbbbbbbbbb")
    desks.desk("session-cccccccccccccccc")
    assert len(desks) == 2 and desks.desk("session-aaaaaaaaaaaaaaaa") is not first  # the oldest was dropped
    now[0] = 100.0
    desks.desk("session-dddddddddddddddd")
    assert len(desks) == 1  # idle sessions expired


def test_sources_show_sweden_as_planned_not_as_a_failure():
    for sources in (client.get("/api/sources").json(), client.get("/api/list").json()["sources"]):
        scb = next(s for s in sources if s["source"] == "scb")
        assert scb["state"] == "planned" and scb["checked_at"] is None
        assert "not connected yet" in scb["detail"]
        assert not any(s["state"] == "unavailable" for s in sources)


def test_the_list_marks_changes_since_the_last_monday_digest():
    since = client.get("/api/list").json()["since"]
    assert since == "2026-10-12T07:00:00+03:00"  # today is pinned to Sat 17 Oct 2026; Helsinki summer time


PROSE_FIELDS = {
    "deciding_rule",
    "rule",
    "why",
    "text",
    "fit_label",
    "explanation",
    "unknown_reason",
    "upgrade_path",
    "reasons",
    "next_action",
    "action",
    "why_not_next",
    "caveats",
}
DATA_KEY = re.compile(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b")


def _prose_with_keys(value, key=None):
    if isinstance(value, dict):
        return [hit for k, v in value.items() for hit in _prose_with_keys(v, k)]
    if isinstance(value, list):
        return [hit for v in value for hit in _prose_with_keys(v, key)]
    if isinstance(value, str) and key in PROSE_FIELDS and "http" not in value:
        return [f"{key}: {value}"] if DATA_KEY.search(value) else []
    return []


@pytest.mark.parametrize(
    "route",
    [
        "/api/funding?mode=redstone",
        f"/api/companies/{MERIVA}",
        f"/api/companies/{HAVNIO}?mode=redstone",
        "/api/list",
        "/api/alerts",
    ],
)
def test_prose_reads_as_words_not_data_keys(route):
    assert _prose_with_keys(client.get(route).json()) == []


def test_large_responses_are_gzipped():
    response = client.get("/api/funding", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200 and response.headers["content-encoding"] == "gzip"


def test_blind_set_rejects_json_that_is_not_a_list_of_rows():
    for body in ("[1, 2, {}]", '"x"', '{"companies": "nope"}'):
        r = client.post("/api/precision/blind", content=body, headers={"Content-Type": "application/json"})
        assert r.status_code == 422, body
