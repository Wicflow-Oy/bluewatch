"""Senders. The default writes .eml files to the local outbox; SMTP exists only for private demos to our
own inboxes.

Both read OUTREACH_ALLOWLIST from the environment at send time (never from the database or the UI)
and refuse any other recipient, so demo mode is enforced in the sender and not only in the policy.
"""

from __future__ import annotations

import re
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from bluewatch.config import OUTBOX_DIR, settings


class SendRefused(RuntimeError):
    """The sender refused before anything left the machine."""


@dataclass(frozen=True)
class OutboundMessage:
    draft_id: str
    to: str | None  # our team inbox; None means the local file outbox only
    subject: str
    body: str
    from_header: str
    stop_address: str | None  # None until a stop address is set; the body still says "reply STOP"
    would_have_gone_to: str  # organisation name and channel kind, never an address
    idempotency_key: str

    def to_email(self) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self.from_header
        message["To"] = self.to or "undisclosed-recipients:;"
        message["Subject"] = self.subject
        message["Message-ID"] = f"<{self.idempotency_key}@bluewatch.invalid>"
        if self.stop_address:
            message["List-Unsubscribe"] = f"<mailto:{self.stop_address}?subject=STOP%20{self.draft_id}>"
        message["X-BlueWatch-Mode"] = "demo"
        message["X-BlueWatch-Would-Have-Gone-To"] = self.would_have_gone_to
        message.set_content(self.body)
        return message


@dataclass(frozen=True)
class SendResult:
    provider: str
    message_id: str
    detail: str
    duplicate: bool = False


def _check_recipient(to: str | None, *, file_only_ok: bool) -> None:
    s = settings()
    if s.outreach_mode != "demo":
        raise SendRefused("Sending is off in this workspace.")
    if to is None:
        if not file_only_ok:
            raise SendRefused("No team inbox is set in OUTREACH_ALLOWLIST, so there is nowhere safe to send.")
        return
    if to.strip().lower() not in s.outreach_allowlist:
        raise SendRefused("The recipient is not on OUTREACH_ALLOWLIST; this workspace sends only to our own inboxes.")


class FileOutbox:
    """Writes each message once to data/outbox/ (gitignored). Nothing is transmitted."""

    name = "file_outbox"

    def __init__(self, directory: Path | str | None = None) -> None:
        self.directory = Path(directory or OUTBOX_DIR)

    def send(self, message: OutboundMessage) -> SendResult:
        _check_recipient(message.to, file_only_ok=True)
        path = self.directory / f"{re.sub(r'[^A-Za-z0-9_-]', '_', message.idempotency_key)}.eml"
        if path.exists():  # the idempotency key makes a retry a no-op, never a second message
            return SendResult(self.name, path.name, f"already in the outbox as {path.name}", duplicate=True)
        self.directory.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(message.to_email()))
        return SendResult(self.name, path.name, f"written to the outbox as {path.name}")


class SmtpSender:
    """SMTP from the SMTP_* env settings, to allowlisted team inboxes only. Never used in tests."""

    name = "smtp"

    def __init__(self, connect=smtplib.SMTP) -> None:
        self._connect = connect

    def send(self, message: OutboundMessage) -> SendResult:
        _check_recipient(message.to, file_only_ok=False)
        s = settings()
        if not s.smtp_host:
            raise SendRefused("SMTP_HOST is not set.")
        with self._connect(s.smtp_host, s.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password or "")
            smtp.send_message(message.to_email())
        return SendResult(self.name, message.idempotency_key, f"sent by SMTP to {message.to}")
