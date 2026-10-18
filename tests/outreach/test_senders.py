import pytest

from bluewatch.outreach.senders import FileOutbox, OutboundMessage, SendRefused, SmtpSender
from tests.outreach.conftest import TEAM_INBOX


def message(to: str | None) -> OutboundMessage:
    return OutboundMessage(
        draft_id="od-1",
        to=to,
        subject="Hello",
        body="Body",
        from_header="Demo <stop@x.test>",
        stop_address="stop@x.test",
        would_have_gone_to="Meriva Oy (org_generic)",
        idempotency_key="od-1-abc",
    )


def never_connect(*args, **kwargs):
    raise AssertionError("SMTP must refuse before connecting")


def test_file_outbox_refuses_addresses_outside_the_allowlist(tmp_path):
    with pytest.raises(SendRefused, match="not on OUTREACH_ALLOWLIST"):
        FileOutbox(tmp_path).send(message("info@meriva.fi"))
    assert list(tmp_path.iterdir()) == []


def test_file_outbox_writes_each_message_once(tmp_path):
    outbox = FileOutbox(tmp_path)
    first, second = outbox.send(message(TEAM_INBOX)), outbox.send(message(TEAM_INBOX))
    assert not first.duplicate and second.duplicate and len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("to", ["info@meriva.fi", None])
def test_smtp_refuses_before_connecting(to):
    with pytest.raises(SendRefused):
        SmtpSender(connect=never_connect).send(message(to))


def test_smtp_needs_a_host_even_for_the_team_inbox():
    with pytest.raises(SendRefused, match="SMTP_HOST"):
        SmtpSender(connect=never_connect).send(message(TEAM_INBOX))
