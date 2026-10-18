"""The Meriva Oy demo case (bridges_seed.json B9 and its gap ledger) as contract objects."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from bluewatch.models import (
    Bridge,
    BridgeEvidence,
    BridgeParty,
    Company,
    Evidence,
    GapLedger,
    NextCheck,
    Registry,
    Resolution,
)
from bluewatch.outreach.desk import Desk
from bluewatch.outreach.senders import FileOutbox
from bluewatch.store import Store

TEAM_INBOX = "team-inbox@bluewatch.test"
SEEN = datetime(2026, 10, 17, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def outreach_env(monkeypatch):
    """Demo mode with one team inbox; the identity from its demo defaults; never the public app."""
    monkeypatch.setenv("OUTREACH_ALLOWLIST", TEAM_INBOX)
    monkeypatch.setenv("BLUEWATCH_PUBLIC", "0")
    for name in (
        "OUTREACH_SENDER_ORG",
        "OUTREACH_SENDER_BUSINESS_ID",
        "OUTREACH_SENDER_ADDRESS",
        "OUTREACH_STOP_ADDRESS",
        "OUTREACH_PRIVACY_URL",
        "SMTP_FROM",
        "SMTP_USER",
        "SMTP_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)


def make_company(state: str = "resolved") -> Company:
    return Company(
        id="FI:3652359-1",
        names=["Meriva Oy"],
        registry=Registry(
            country="FI", id="3652359-1", name="Meriva Oy", founded=date(2026, 9, 3), municipality="Turku"
        ),
        domain="meriva.fi",
        vertical="blue_biotech_water",
        resolution=Resolution(state=state, reason="business ID shown on the company's own site"),
    )


@pytest.fixture
def company() -> Company:
    return make_company()


def _ev(n: int, field: str, claim: str, **kw) -> Evidence:
    return Evidence(
        id=f"FI:3652359-1#{n:02d}", company_id="FI:3652359-1", field=field, claim=claim, first_seen_at=SEEN, **kw
    )


@pytest.fixture
def ledger() -> GapLedger:
    prh = "https://avoindata.prh.fi/opendata-ytj-api/v3/companies?businessId=3652359-1"
    return GapLedger(
        company_id="FI:3652359-1",
        facts=[
            _ev(1, "founded", "Founded 3 Sep 2026", url=prh, source_family="prh", tag="registry"),
            _ev(
                2,
                "product",
                "Aquaculture consulting, project planning, training and R&D",
                quote="Aquaculture consulting",
                url="https://www.meriva.fi/",
                source_family="site:meriva.fi",
                tag="site",
                verified_quote=True,
            ),
            _ev(3, "team", "Team of five", source_family="snippet", tag="snippet"),  # not verified
        ],
        unknowns=[
            _ev(
                4,
                "team",
                "Team unknown",
                state="unknown",
                source_family="site:meriva.fi",
                tag="site",
                why_unknown="No team page",
                next_check=NextCheck(
                    kind="public_check", how="Re-read the site in 4 weeks", question="Who is on the team?"
                ),
            ),
            _ev(
                5,
                "customers_or_sites",
                "Customers unknown",
                state="unknown",
                source_family="site:meriva.fi",
                tag="site",
                why_unknown="No references on the site",
                next_check=NextCheck(kind="ask_founder"),
            ),
            _ev(
                6,
                "funding_events",
                "Funding unknown",
                state="unknown",
                source_family="prh",
                tag="registry",
                next_check=NextCheck(kind="public_check", how="PRH notices by business ID, monthly"),
            ),
        ],
    )


@pytest.fixture
def evidence(ledger) -> list[Evidence]:
    return ledger.facts + ledger.unknowns


@pytest.fixture
def bridge() -> Bridge:
    return Bridge(
        id="B9",
        type="programme_fit",
        company=BridgeParty(name="Meriva Oy", country="FI", registry_id="3652359-1", company_id="FI:3652359-1"),
        counterparty=BridgeParty(name="A'Pelago Northern Blue 2027", kind="programme"),
        reason="A Turku aquaculture consultancy founded 3 Sep 2026: a likely mentor or expert for the next cohort",
        evidence_company=[BridgeEvidence(claim="Founded 2026-09-03 in Turku (PRH)", tag="registry")],
        evidence_counterparty=[BridgeEvidence(claim="Northern Blue 2027 applications open", tag="dossier")],
        action="Invite as an aquaculture mentor or expert for Northern Blue 2027",
        confidence="possible",
        mode="apelago",
    )


@pytest.fixture
def outbox(tmp_path):
    return tmp_path / "outbox"


@pytest.fixture
def desk(tmp_path, outbox) -> Desk:
    return Desk(Store(tmp_path / "desk.db"), sender=FileOutbox(outbox))
