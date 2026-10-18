"""Register addresses never leave the server: only the municipality does (a new company is often registered at a
founder's home, and a c/o line can name a person)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bluewatch import net
from bluewatch.api import app as app_module
from bluewatch.api import deps
from bluewatch.api.guards import RateLimiter
from bluewatch.sources import brreg, prh, rik

client = TestClient(app_module.app)
FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
ADDRESS_KEYS = {"street", "postCode", "buildingNumber", "apartmentNumber", "co", "zip_code", "adresse", "postnummer"}
PRIVATE = ["c/o ", "Testi Henkilö", "Ola Nordmann", "Kotikatu", "00100", "Hjemveien", "0150", "Kodutänav", "10111"]

PRH_COMPANY = {
    "businessId": {"value": "1234567-1", "registrationDate": "2026-10-13"},
    "names": [{"name": "Testimeri Oy", "type": "1"}],
    "companyForms": [{"type": "16", "descriptions": [{"languageCode": "3", "description": "Limited company"}]}],
    "tradeRegisterStatus": "1",
    "addresses": [
        {
            "type": 1,
            "street": "Kotikatu",
            "postCode": "00100",
            "buildingNumber": "5",
            "apartmentNumber": "12",
            "co": "c/o Testi Henkilö",
            "postOffices": [{"city": "HELSINKI", "languageCode": "1", "municipalityCode": "091"}],
        }
    ],
}
BRREG_ENTITY = {
    "organisasjonsnummer": "123456785",
    "navn": "TESTHAV AS",
    "organisasjonsform": {"kode": "AS"},
    "stiftelsesdato": "2026-10-13",
    "forretningsadresse": {
        "adresse": ["c/o Ola Nordmann", "Hjemveien 5"],
        "postnummer": "0150",
        "poststed": "OSLO",
        "kommune": "OSLO",
        "kommunenummer": "0301",
        "landkode": "NO",
    },
}
RIK_HIT = {
    "reg_code": 12345678,
    "name": "Testmeri OÜ",
    "status": "R",
    "legal_form": "5",
    "legal_address": "Harju maakond, Tallinn, Kesklinna linnaosa, Kodutänav 5-12",
    "zip_code": "10111",
}


def _answer(url: str, params: dict | None = None, **_: object) -> net.CachedResponse:
    if url == prh.YTJ:
        body: dict = {"totalResults": 1, "companies": [PRH_COMPANY]}
    elif url.startswith(prh.NOTICES):
        body = {"publicNotices": []}
    elif url == f"{brreg.API}/enheter/123456785":
        body = BRREG_ENTITY
    elif url.startswith(f"{brreg.API}/enheter"):
        body = {"_embedded": {"enheter": [BRREG_ENTITY]}, "page": {"totalElements": 1}}
    elif url == rik.AUTOCOMPLETE:
        body = {"status": "OK", "data": [RIK_HIT]}
    else:
        raise AssertionError(f"unexpected request: {url} {params}")
    return net.CachedResponse(url, 200, json.dumps(body), datetime.now(timezone.utc), False)


@pytest.fixture(autouse=True)
def live_registers(monkeypatch):
    monkeypatch.setenv("BLUEWATCH_LIVE_LOOKUPS", "1")
    monkeypatch.setattr(net, "get", _answer)
    monkeypatch.setattr(deps, "_limiter", RateLimiter(per_ip_per_hour=1000, total_per_minute=1000))


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


@pytest.mark.parametrize(
    ("country", "business_id", "municipality"),
    [("FI", "1234567-1", "Helsinki"), ("NO", "123456785", "Oslo"), ("EE", "12345678", "Tallinn")],
)
@pytest.mark.parametrize("route", ["/api/lookup", "/api/founder", "/api/lookup/card"])
def test_lookups_return_the_municipality_and_no_address(route, country, business_id, municipality):
    response = client.post(route, json={"country": country, "business_id": business_id})
    assert response.status_code == 200
    text = response.text
    assert municipality in text  # the register answer was used
    assert not [p for p in PRIVATE if p in text] and not _keys(response.json()) & ADDRESS_KEYS


def test_name_search_returns_no_address():
    response = client.post("/api/search", json={"query": "testimeri"})
    assert response.status_code == 200 and "Testimeri Oy" in response.text
    assert not [p for p in PRIVATE if p in response.text] and not _keys(response.json()) & ADDRESS_KEYS


def test_recorded_fixtures_hold_no_c_o_lines_or_street_addresses():
    found = []
    for path in sorted(FIXTURES.rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        if "c/o " in text.lower():
            found.append(f"{path.name}: c/o line")
        if keys := _keys(json.loads(text)) & ADDRESS_KEYS:
            found.append(f"{path.name}: {sorted(keys)}")
    assert not found
