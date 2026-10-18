import builtins
import logging
import pathlib
from datetime import date, datetime, timezone

import pytest

from bluewatch.founder.view import CONSENT_TEXT_VERSION, evaluate, profile_from_registry, record_consent
from bluewatch.models import Registry

TODAY = date(2026, 10, 17)
MERIVA = Registry(
    country="FI", id="3652359-1", name="Meriva Oy", founded=date(2026, 9, 3), form="OY", municipality="Turku"
)
HAVNIO = Registry(
    country="NO",
    id="938525420",
    name="HAVNIO AS",
    founded=date(2026, 9, 16),
    form="AS",
    industry_code="62.100",
    municipality="Stavanger",
)


def tiers(registry: Registry, **kw) -> dict:
    view = evaluate(profile_from_registry(registry), TODAY, **kw)
    return {t.instrument_id: t for t in view.tiers}


def test_sbep_call_4_flips_from_excluded_to_possible():
    meriva, havnio = tiers(MERIVA)["sbep-jtc4"], tiers(HAVNIO)["sbep-jtc4"]
    assert meriva.tier == "excluded" and meriva.rule_verified
    assert "no Finnish funder" in meriva.deciding_rule
    assert havnio.tier == "possible"
    assert meriva.deadline == havnio.deadline == date(2026, 11, 16)


def test_national_instruments_switch_with_the_country():
    fi, no = tiers(MERIVA), tiers(HAVNIO)
    assert fi["bf-sprint"].tier in ("likely", "possible") and no["bf-sprint"].tier == "excluded"
    norwegian = "rcn-innovation-project-industrial-energy-transport-2026"
    assert fi[norwegian].tier == "excluded"
    assert fi["innovation-norway-miljoteknologi"].tier == "excluded"
    assert no["innovation-norway-miljoteknologi"].tier != "excluded"


def test_a_bare_registry_gives_unknowns_not_errors():
    bare = Registry(country="FI", id="3652359-1")
    profile = profile_from_registry(bare)
    assert profile.founded is None and profile.themes == []
    view = evaluate(profile, TODAY, registry=bare)
    sprint = next(t for t in view.tiers if t.instrument_id == "bf-sprint")
    assert sprint.tier in ("likely", "possible")  # unknowns, never an error and never "certain"
    assert view.rules_version.startswith("rules-")


def test_industry_code_pending_is_an_unknown_rule():
    from bluewatch.rules.eligibility import applicant_from_profile
    from bluewatch.rules.funding import evaluate as evaluate_instrument
    from bluewatch.rules.funding import instruments

    sprint = next(i for i in instruments() if i["id"] == "bf-sprint")
    applicant = applicant_from_profile(profile_from_registry(MERIVA), TODAY, MERIVA)
    checks = evaluate_instrument(sprint, applicant, TODAY).checks
    assert any(c.outcome == "unknown" and "industry code not yet registered" in c.text for c in checks)


def test_a_sole_trader_view_shows_no_details():
    person = Registry(country="FI", id="1234567-8", name="Matti Meikäläinen", natural_person=True)
    profile = profile_from_registry(person)
    assert profile.name is None and profile.business_id is None and profile.founded is None
    view = evaluate(profile, TODAY)
    assert view.tiers == view.programmes == view.investors == view.next_30_days == []
    assert "Meik" not in view.model_dump_json() and "1234567-8" not in view.model_dump_json()


def test_view_has_programmes_investors_and_dated_next_steps():
    view = evaluate(profile_from_registry(HAVNIO), TODAY, registry=HAVNIO)
    assert view.programmes and view.investors
    dated = [s for s in view.next_30_days if s.deadline]
    assert all(0 <= (s.deadline - TODAY).days <= 30 for s in dated)
    assert dated and not any(str(s.deadline.year) in s.action for s in dated)  # the deadline chip shows the date
    assert [s.rank for s in view.next_30_days] == list(range(1, len(view.next_30_days) + 1))


@pytest.fixture
def no_writes(monkeypatch):
    real_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            raise AssertionError(f"the founder view must not write files ({file})")
        return real_open(file, mode, *args, **kwargs)

    def refuse(*args, **kwargs):
        raise AssertionError("the founder view must not write files")

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(pathlib.Path, "write_text", refuse)
    monkeypatch.setattr(pathlib.Path, "write_bytes", refuse)


def test_evaluate_is_pure(no_writes, caplog):
    caplog.set_level(logging.DEBUG)
    profile = profile_from_registry(HAVNIO)
    first, second = evaluate(profile, TODAY, registry=HAVNIO), evaluate(profile, TODAY, registry=HAVNIO)
    assert first == second
    assert not any("938525420" in r.getMessage() for r in caplog.records)  # the ID is never logged


def test_record_consent_only_builds_the_object(no_writes):
    at = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    consent = record_consent("FI:3652359-1", ["business_id", "tier_results"], now=at)
    assert consent.given and consent.given_at == at and consent.withdrawn_at is None
    assert consent.consent_text_version == CONSENT_TEXT_VERSION
    with pytest.raises(ValueError):
        record_consent("FI:3652359-1", ["email"])
    with pytest.raises(ValueError):
        record_consent("FI:3652359-1", [])


def test_unknown_themes_cap_a_themed_call_at_possible():
    """Meriva's register record says nothing about its themes, so EMSO physical access (themed: ocean
    observation, marine sensors) can't be "likely" for it, however clean the other rules are."""
    meriva_tiers = evaluate(profile_from_registry(MERIVA), TODAY).tiers
    emso = next(t for t in meriva_tiers if t.instrument_id == "emso-physical-access-2026")
    assert emso.tier == "possible" and "themes are not known" in emso.deciding_rule
    assert emso.upgrade_path
    for tier in meriva_tiers:
        if "themes are not known" in tier.deciding_rule or "Theme fit not mapped" in tier.deciding_rule:
            assert tier.tier in ("possible", "excluded", "unknown")


def test_a_company_with_a_card_gets_the_same_tier_per_call_as_the_funding_page():
    """Founder view and the funding page read the same researched facts: one verdict per call, and a call
    the funding page excludes never shows up as a next step."""
    from fastapi.testclient import TestClient

    from bluewatch.api.app import app

    client = TestClient(app)
    founder = client.post("/api/founder", json={"country": "FI", "business_id": "3652359-1"}).json()
    assert founder["lookup"]["company_id"] == "FI:3652359-1"
    view = {t["instrument_id"]: t["tier"] for t in founder["view"]["tiers"]}
    catalogue = client.get("/api/funding?mode=apelago").json()
    funding = {
        i["id"]: t["tier"] for i in catalogue["instruments"] for t in i["tiers"] if t["company_id"] == "FI:3652359-1"
    }
    assert funding and view == funding
    assert funding["eic-pathfinder-challenges-2026"] == "excluded"
    excluded = {iid for iid, tier in funding.items() if tier == "excluded"}
    assert not {s["opportunity_id"].split(":")[-1] for s in founder["view"]["next_30_days"]} & excluded
