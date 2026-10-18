from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from bluewatch import seed
from bluewatch.models import (
    CONTRACTS_VERSION,
    DIMENSIONS,
    Assessment,
    Company,
    DimensionState,
    EntityRef,
    Evidence,
    ReadinessLevel,
    Registry,
    Resolution,
    Score,
    Signal,
)


def test_version_and_dimensions():
    assert CONTRACTS_VERSION.count(".") == 2
    assert len(DIMENSIONS) == 10


def test_round_trip_company_and_assessment():
    company = Company(
        id="NO:938525420",
        names=["HAVNIO AS"],
        registry=Registry(country="NO", id="938525420", form="AS"),
        domain="havnio.no",
        vertical="maritime_ports",
        resolution=Resolution(state="resolved", reason="Brreg ID matches the site domain"),
    )
    assert Company.model_validate_json(company.model_dump_json()) == company
    assessment = Assessment(
        company_id=company.id,
        levels=[ReadinessLevel(key="trl", level=None, unknown_reason="No live app checked")],
        dimensions=[DimensionState(key=k, state="unknown") for k in DIMENSIONS],
        score=Score(potential=0.7, evidence=0.3, group="dive_deeper"),
        rules_version="test",
        assessed_at=datetime(2026, 10, 17, tzinfo=timezone.utc),
    )
    assert assessment.levels[0].level is None  # unknown is None, never 0


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        Evidence(id="e1", field="x", claim="c", source_family="prh", tag="registry", surprise=1)


def test_signal_minimal():
    s = Signal(
        id="prh:3652359-1:newly_founded",
        source="prh",
        type="newly_founded",
        entity_ref=EntityRef(registry="prh", id="3652359-1"),
        first_seen_at=datetime(2026, 10, 17, tzinfo=timezone.utc),
        hash="abc",
    )
    assert s.sensitivity == "public"


def test_seeds_load():
    assert len(seed.load("investors")["investors"]) == 60
    assert len(seed.load("bridges")["bridges"]) == 10


def test_empty_env_values_fall_back_to_defaults(monkeypatch):
    from bluewatch.config import HELSINKI, settings

    for name in (
        "BLUEWATCH_DAILY_SPEND_CAP_USD",
        "BLUEWATCH_TODAY",
        "BLUEWATCH_LOOKUPS_PER_IP_PER_HOUR",
        "BLUEWATCH_LOOKUPS_PER_MINUTE_TOTAL",
        "SMTP_PORT",
        "BLUEWATCH_CLASSIFIER_MODEL",
    ):
        monkeypatch.setenv(name, "")
    s = settings()
    assert s.daily_spend_cap_usd == 40.0
    assert s.today == datetime.now(HELSINKI).date()
    assert (s.lookups_per_ip_per_hour, s.lookups_per_minute_total) == (300, 120)
    assert s.classifier_model == "claude-haiku-5-5"
