from datetime import date

import pytest

from bluewatch.config import settings
from bluewatch.llm import FakeModelClient
from bluewatch.models import Opportunity
from bluewatch.outreach.drafts import POLISH_TASK, DraftRefused, evidence_request, first_touch
from bluewatch.outreach.templates import LANGUAGES, SenderIdentity, footer_problems
from tests.outreach.conftest import make_company


@pytest.mark.parametrize("language", LANGUAGES)
def test_footer_is_complete_in_every_language(company, ledger, bridge, language):
    draft = evidence_request(company, ledger, bridge, language=language)
    identity = SenderIdentity.from_env(settings())
    assert footer_problems(draft.body, language, identity, "Meriva Oy") == []
    assert identity.stop_address in draft.body.rsplit("\n----\n", 1)[1]
    assert "**" not in draft.body  # sent as plain text: markup would reach the reader as asterisks


@pytest.mark.parametrize("language", LANGUAGES)
def test_footer_check_finds_a_missing_stop_line(company, ledger, bridge, language):
    draft = evidence_request(company, ledger, bridge, language=language)
    without_stop = draft.body.rsplit("\n\n", 1)[0]
    problems = footer_problems(without_stop, language, SenderIdentity.from_env(settings()), "Meriva Oy")
    assert problems == ["footer: separate stop line with a stop address is missing"]


@pytest.mark.parametrize("state", ["probable", "ambiguous", "unconfirmed", "unresolved"])
def test_only_resolved_companies_can_be_drafted(ledger, bridge, state):
    with pytest.raises(DraftRefused, match=state):
        evidence_request(make_company(state), ledger, bridge)


def test_two_questions_close_the_biggest_askable_gaps(company, ledger, bridge):
    draft = evidence_request(company, ledger, bridge, language="fi")
    unknown_ids = {e.id for e in ledger.unknowns}
    assert [q.evidence_id for q in draft.questions] == ["FI:3652359-1#05", "FI:3652359-1#04"]  # customers, team
    assert {q.evidence_id for q in draft.questions} <= unknown_ids & set(draft.evidence_ids)
    assert "FI:3652359-1#06" not in draft.evidence_ids  # a public check we run ourselves is not asked
    assert "A'Pelago Northern Blue 2027" in draft.body and "Nimiä ei tarvita" in draft.body
    assert draft.mode == "evidence_request" and draft.bridge_id == "B9" and draft.status == "draft"


def test_first_touch_offers_without_questions(company, bridge):
    draft = first_touch(company, bridge, language="sv")
    assert draft.mode == "first_touch" and draft.questions == []
    assert "A'Pelago Northern Blue 2027" in draft.subject and "30 minuter" in draft.subject
    assert "30 minuter" in draft.body


def test_a_draft_is_personal_and_asks_for_an_intro_call(company, ledger, bridge):
    draft = evidence_request(company, ledger, bridge, language="en")
    assert draft.subject.startswith("Meriva Oy: ") and draft.subject.endswith(", and a 30-minute intro call?")
    assert "We noticed that Meriva Oy was registered on" in draft.body
    assert "30-minute intro call" in draft.body
    assert draft.body.index("30-minute intro call") < draft.body.index("Before we talk")


def test_a_useful_opportunity_is_required(company, ledger):
    with pytest.raises(DraftRefused, match="one useful opportunity"):
        evidence_request(company, ledger, None)
    excluded = Opportunity(
        id="op1", company_id=company.id, kind="grant", title="SBEP call 4", tier="excluded", action="none"
    )
    with pytest.raises(DraftRefused, match="excluded"):
        evidence_request(company, ledger, excluded)


def test_a_past_deadline_is_not_offered(company, ledger, bridge):
    with pytest.raises(DraftRefused, match="passed"):
        evidence_request(company, ledger, bridge.model_copy(update={"deadline": date(2026, 10, 1)}))


def test_polish_only_sees_verified_evidence(company, ledger, bridge):
    model = FakeModelClient(
        answers={
            POLISH_TASK: {"paragraph": "We are a demo team. A'Pelago Northern Blue 2027 could suit Meriva Oy now."}
        }
    )
    draft = evidence_request(company, ledger, bridge, model=model)
    prompt = model.calls[0].prompt
    assert "Aquaculture consulting" in prompt and "Founded 3 Sep 2026" in prompt
    assert "Team of five" not in prompt  # a search snippet is not verified evidence
    assert draft.body.split("\n\n")[1].startswith("We are a demo team.")
    assert draft.audit[-1].detail.endswith("polished")


@pytest.mark.parametrize(
    "paragraph, why",
    [
        ("A'Pelago Northern Blue 2027 pays EUR 50,000 to Meriva Oy.", "added a number"),
        ("A'Pelago Northern Blue 2027: see https://evil.example/now", "added a link"),
        ("Write to anna.virtanen@meriva.example about A'Pelago Northern Blue 2027.", "added an e-mail address"),
        ("We would love to talk to you soon.", "dropped the offer"),
    ],
)
def test_polish_that_adds_facts_is_dropped(company, ledger, bridge, paragraph, why):
    draft = evidence_request(
        company, ledger, bridge, model=FakeModelClient(answers={POLISH_TASK: {"paragraph": paragraph}})
    )
    assert paragraph not in draft.body
    assert why in draft.audit[-1].detail


def test_a_refused_polish_keeps_the_template(company, ledger, bridge):
    draft = evidence_request(company, ledger, bridge, model=FakeModelClient())  # no answer: a refusal
    assert "no usable paragraph" in draft.audit[-1].detail
    assert "could be a good fit for you now" in draft.body


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_named_sender_gives_its_business_id_and_privacy_notice(monkeypatch, company, ledger, bridge, language):
    monkeypatch.setenv("OUTREACH_SENDER_ORG", "Ocean Ventures Oy")
    monkeypatch.setenv("OUTREACH_SENDER_BUSINESS_ID", "1234567-8")
    monkeypatch.setenv("OUTREACH_SENDER_ADDRESS", "Turku")
    monkeypatch.setenv("OUTREACH_PRIVACY_URL", "https://example.org/privacy")
    draft = evidence_request(company, ledger, bridge, language=language, workspace="redstone")
    identity = SenderIdentity.from_env(settings(), "redstone")
    foot = draft.body.rsplit("\n----\n", 1)[1]
    assert identity.complete and "Ocean Ventures Oy (" in foot and "1234567-8, Turku" in foot
    assert "https://example.org/privacy" in foot
    assert footer_problems(draft.body, language, identity, "Meriva Oy") == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_an_unset_sender_says_so_instead_of_showing_placeholders(company, ledger, bridge, language):
    draft = evidence_request(company, ledger, bridge, language=language, workspace="redstone")
    assert "Redstone" in draft.body.split("\n\n")[1]  # "We are Redstone."
    assert "DEMO-" not in draft.body and ".invalid" not in draft.body
    assert not any(word in draft.body for word in ("marketing", "markkinointi", "marknadsföring"))
