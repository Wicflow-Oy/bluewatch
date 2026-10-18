"""A company the register lists as closed is no lead: its live card and founder view build no programmes,
investors or next steps, and the lookup says plainly that it no longer trades."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from bluewatch import demo
from bluewatch.api import deps
from bluewatch.api.app import app
from bluewatch.api.guards import RateLimiter
from bluewatch.models import ConnectorResult, Registry, SourceStatus
from bluewatch.sources import brreg

BANKRUPT = Registry(
    country="NO",
    id="923485155",
    name="BETTEN FISK AS",
    founded=date(2019, 8, 1),
    form="AS",
    industry_code="03.211",
    status="bankrupt",
)
client = TestClient(app)


@pytest.fixture(autouse=True)
def register_answers(monkeypatch):
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1000, total_per_minute=1000))
    status = SourceStatus(source="brreg", label="Brreg", state="live")
    monkeypatch.setattr(brreg, "lookup_result", lambda _id: ConnectorResult(records=[BANKRUPT], status=status))


def test_a_closed_company_card_builds_no_leads_and_says_it_no_longer_trades():
    card = demo.live_card(BANKRUPT, "apelago")
    assert not (card.opportunities or card.investors or card.bridges or card.next_steps)
    score = card.assessment.score
    assert score.group == "not_for_us" and score.potential == 0.0 and "closed" in card.assessment.flags
    assert score.explanation[-1] == "Not for us: no longer trading (register status: bankrupt)"
    trading = demo.live_card(BANKRUPT.model_copy(update={"status": None}), "apelago")
    assert trading.opportunities and trading.investors  # the same record while it trades does get leads


@pytest.mark.parametrize("path", ["/api/founder", "/api/lookup/card"])
def test_the_api_builds_nothing_for_it_and_the_lookup_says_why(path):
    body = client.post(f"{path}?lang=fi", json={"country": "NO", "business_id": "923485155"}).json()
    assert body["lookup"]["closed"]
    assert body["lookup"]["message"] == (
        "Yritys ei enää toimi (rekisterin tila: konkurssissa), joten ohjelmia, sijoittajia tai seuraavia "
        "askelia ei näytetä."
    )
    built = body.get("view") or body.get("card")
    assert built and not any(built.get(key) for key in ("tiers", "programmes", "investors", "next_30_days"))
    assert not any(built.get(key) for key in ("opportunities", "bridges", "next_steps"))
