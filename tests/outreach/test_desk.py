from datetime import datetime, timedelta, timezone
from email import message_from_bytes

import pytest

from bluewatch.config import Settings
from bluewatch.models import Channel, Evidence
from bluewatch.outreach.desk import PUBLIC_DEMO_NOTE, Desk, DeskError
from bluewatch.outreach.drafts import evidence_request, text_hash
from bluewatch.outreach.senders import FileOutbox
from bluewatch.store import Store
from tests.outreach.conftest import TEAM_INBOX

INFO = Channel(kind="org_generic", address="info@meriva.fi", source_url="https://www.meriva.fi/")


@pytest.fixture
def pending(desk, company, ledger, bridge, evidence):
    draft = evidence_request(company, ledger, bridge, language="en", channel=INFO)
    return desk.submit(draft, company=company, evidence=evidence)


def approve(desk, draft):
    return desk.approve(draft.id, "lead", text_hash(draft))


def outbox_files(outbox):
    return list(outbox.glob("*.eml")) if outbox.exists() else []


def test_the_full_loop_flips_two_unknowns_to_confirmed(desk, pending, outbox):
    assert pending.status == "pending_approval"
    sent = desk.send(approve(desk, pending).id)
    assert sent.status == "sent" and sent.demo_recipient == TEAM_INBOX and sent.lawful_route == "org_generic"
    [eml] = outbox_files(outbox)
    message = message_from_bytes(eml.read_bytes())
    assert message["To"] == TEAM_INBOX and "info@meriva.fi" not in eml.read_text(encoding="utf-8")
    assert message["List-Unsubscribe"].startswith(f"<mailto:{TEAM_INBOX}")

    reply, confirmed = desk.simulate_reply(
        sent.id, ["Two fish farms in Naantali and a research station.", "Three people with aquaculture backgrounds."]
    )
    assert reply.classification == "answer" and reply.from_domain == "meriva.fi"
    assert [e.id for e in confirmed] == [q.evidence_id for q in sent.questions]
    assert all(e.state == "fact" and e.tag == "company_reply" and e.confirmed_by.draft_id == sent.id for e in confirmed)
    assert desk.get(sent.id).status == "replied"
    actions = [event.action for event in desk.audit_log(sent.id)]
    assert actions == ["submitted", "approved", "sent", "reply_answer"]


def test_nothing_is_sent_without_an_approval(desk, pending, outbox):
    with pytest.raises(DeskError, match="without an approval"):
        desk.send(pending.id)
    assert outbox_files(outbox) == []


def test_approval_needs_the_hash_of_the_text_it_saw(desk, pending):
    with pytest.raises(DeskError, match="changed since you reviewed"):
        desk.approve(pending.id, "lead", "0" * 64)
    assert desk.get(pending.id).status == "pending_approval"


def test_editing_after_approval_voids_it(desk, pending, outbox):
    approved = approve(desk, pending)
    edited = desk.edit(approved.id, editor="lead", body=approved.body.replace("Hello,", "Hello again,"))
    assert edited.status == "pending_approval" and edited.approved_text_hash is None
    with pytest.raises(DeskError):
        desk.send(edited.id)
    assert outbox_files(outbox) == []


def test_text_changed_after_approval_blocks_the_send(desk, pending, outbox):
    approved = approve(desk, pending)
    tampered = approved.model_copy(update={"body": approved.body + "\nP.S. one more claim"})
    desk.store.put("outreach_draft", tampered.id, tampered)  # a change that bypassed edit()
    result = desk.send(tampered.id)
    assert result.status == "pending_approval" and "text changed after approval" in result.audit[-1].detail
    assert outbox_files(outbox) == []


def test_an_approval_expires_after_a_day(tmp_path, company, ledger, bridge, evidence, outbox):
    now = [datetime(2026, 10, 17, 10, tzinfo=timezone.utc)]
    desk = Desk(Store(tmp_path / "d.db"), sender=FileOutbox(outbox), clock=lambda: now[0])
    draft = desk.submit(evidence_request(company, ledger, bridge, channel=INFO), company=company, evidence=evidence)
    approve(desk, draft)
    now[0] += timedelta(hours=25)
    assert desk.send(draft.id).status == "pending_approval"
    assert outbox_files(outbox) == []


def test_suppression_blocks_at_approval(desk, pending, outbox):
    desk.suppression.add(reason="opt_out", domain="meriva.fi")
    result = approve(desk, pending)
    assert result.status == "blocked_suppressed" and "suppression list" in result.audit[-1].detail
    assert outbox_files(outbox) == []


def test_suppression_blocks_at_send(desk, pending, outbox):
    approved = approve(desk, pending)
    desk.suppression.add(reason="opt_out", address="info@meriva.fi")
    assert desk.send(approved.id).status == "blocked_suppressed"
    assert outbox_files(outbox) == []


def test_a_stop_reply_suppresses_the_company(desk, pending, company, ledger, bridge, evidence):
    sent = desk.send(approve(desk, pending).id)
    reply, confirmed = desk.simulate_reply(sent.id, "STOP please")
    assert reply.classification == "opt_out" and confirmed == []
    assert desk.get(sent.id).status == "opted_out"
    again = evidence_request(company, ledger, bridge, channel=INFO)
    assert desk.submit(again, company=company, evidence=evidence).status == "blocked_suppressed"


def test_no_send_outside_the_allowlist(monkeypatch, tmp_path, company, ledger, bridge, evidence, outbox):
    monkeypatch.delenv("OUTREACH_ALLOWLIST")
    desk = Desk(Store(tmp_path / "d.db"), sender=FileOutbox(outbox))
    draft = desk.submit(evidence_request(company, ledger, bridge, channel=INFO), company=company, evidence=evidence)
    sent = desk.send(approve(desk, draft).id)
    assert sent.status == "sent" and sent.demo_recipient == "local file outbox"
    [eml] = outbox_files(outbox)
    assert message_from_bytes(eml.read_bytes())["To"] == "undisclosed-recipients:;"


def test_the_public_app_never_calls_a_sender(tmp_path, company, ledger, bridge, evidence):
    class Exploding:
        def send(self, message):
            raise AssertionError("the public app must never send")

    desk = Desk(Store(tmp_path / "d.db"), sender=Exploding(), settings=Settings(public_mode=True))
    draft = desk.submit(evidence_request(company, ledger, bridge, channel=INFO), company=company, evidence=evidence)
    result = desk.send(approve(desk, draft).id)
    assert result.status == "blocked_demo" and result.audit[-1].detail == PUBLIC_DEMO_NOTE
    reply, confirmed = desk.simulate_reply(result.id, {draft.questions[0].evidence_id: "Two fish farms."})
    assert len(confirmed) == 1 and desk.get(draft.id).status == "replied"


def test_no_personal_address_is_stored(tmp_path, company, ledger, bridge, evidence, outbox):
    db = tmp_path / "d.db"
    desk = Desk(Store(db), sender=FileOutbox(outbox))
    role_check = Evidence(
        id="rc1",
        company_id=company.id,
        field="role_check",
        claim="CEO per PRH",
        url="https://avoindata.prh.fi/",
        source_family="prh",
        tag="registry",
    )
    for channel in (
        Channel(kind="org_generic", address="firstname.lastname@meriva.fi"),
        Channel(kind="named_role", address="matti.meikalainen@meriva.fi", role_check_evidence_id="rc1"),
    ):
        draft = evidence_request(company, ledger, bridge, channel=channel)
        stored = desk.submit(draft, company=company, evidence=[*evidence, role_check])
        assert stored.status == "draft" and stored.channel.kind == "personal_blocked" and stored.channel.address is None
        assert "blocked in code" in desk.decision(stored.id).reasons[0]
    raw = db.read_bytes()
    assert b"firstname.lastname" not in raw and b"meikalainen" not in raw
    assert outbox_files(outbox) == []


def test_a_named_role_needs_a_stored_role_check(desk, company, ledger, bridge, evidence):
    ceo = Channel(kind="named_role", address="ceo@meriva.fi", role_check_evidence_id="rc-missing")
    stored = desk.submit(evidence_request(company, ledger, bridge, channel=ceo), company=company, evidence=evidence)
    assert stored.status == "draft" and stored.risk == "high"
    assert any("role check" in r for r in desk.decision(stored.id).reasons)


def test_questions_must_close_stored_unknowns(desk, company, ledger, bridge):
    stored = desk.submit(evidence_request(company, ledger, bridge, channel=INFO), company=company)
    assert stored.status == "draft"
    assert any("stored unknown" in r for r in desk.decision(stored.id).reasons)
