"""The progressive live card: the register card at once, then the same card with the company's website read."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bluewatch.api import app as app_module
from bluewatch.api import deps
from bluewatch.api.app import app
from bluewatch.api.guards import RateLimiter
from bluewatch.models import Evidence
from bluewatch.read.live import SiteRead, SiteReading
from bluewatch.sources import prh

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1000, total_per_minute=1000))


@pytest.fixture(scope="module")
def outside() -> str:
    """A Finnish company in the recorded register data but not in the precomputed set."""
    known = {r["id"] for r in client.get("/api/companies").json()}
    return next(r.id for r in prh._recorded_index().values() if f"FI:{r.id}" not in known and not r.natural_person)


def test_without_a_key_the_read_says_it_is_off_and_keeps_the_register_card(outside):
    body = {"country": "FI", "business_id": outside}
    register = client.post("/api/lookup/card", json=body).json()
    read = client.post("/api/lookup/card/read", json=body).json()
    assert read["read"] == {
        "state": "off",
        "host": None,
        "url": None,
        "read_at": None,
        "found_in_register": False,
        "claims": 0,
    }
    assert read["card"]["assessment"]["score"] == register["card"]["assessment"]["score"]
    assert client.get("/api/meta").json()["live_reader"] is False


def test_a_read_site_adds_its_claims_and_reassesses(outside, monkeypatch):
    company_id = f"FI:{outside}"
    claim = Evidence(
        id=f"{company_id}:site:customers:1",
        company_id=company_id,
        field="customers",
        claim="Customers are ports.",
        value="ports",
        quote="We serve ports in Finland",
        url="https://example.fi/",
        source_family="site:example.fi",
        tag="llm",
        verified_quote=True,
    )
    reading = SiteReading(
        SiteRead(state="read", host="example.fi", url="https://example.fi/", claims=1), [claim], "maritime_ports"
    )
    monkeypatch.setattr(app_module.site_reader, "read_site", lambda company: reading)
    read = client.post("/api/lookup/card/read", json={"country": "FI", "business_id": outside}).json()
    card = read["card"]
    assert read["read"]["state"] == "read" and read["read"]["host"] == "example.fi"
    assert card["company"]["vertical"] == "maritime_ports" and card["company"]["domain"] == "example.fi"
    assert claim.id in {e["id"] for e in card["ledger"]["facts"]}


def test_a_precomputed_company_has_no_read(monkeypatch):
    monkeypatch.setattr(app_module.site_reader, "read_site", lambda company: pytest.fail("read a known company"))
    read = client.post("/api/lookup/card/read", json={"country": "FI", "business_id": "3652359-1"}).json()
    assert read["read"] is None and read["card"] is None and read["lookup"]["company_id"] == "FI:3652359-1"
