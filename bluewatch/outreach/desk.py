"""The outreach desk: the approval state machine around every message.

    draft -> pending_approval -> approved | rejected
    approved -> sent | blocked_demo | blocked_suppressed
    sent -> replied | bounced | opted_out

A person approves every message, and the approval binds to a hash of the exact text and recipient
channel: if either changes, the approval is void and nothing is sent. The policy runs at submit, at
approval and again at send (an organisation may object in between). The deployed public app never
sends at all. Every step goes to the append-only audit table in bluewatch/store.py.
"""

from __future__ import annotations

import re
import smtplib
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from bluewatch.config import Settings
from bluewatch.config import settings as load_settings
from bluewatch.models import (
    AuditEvent,
    Company,
    Confirmation,
    DraftStatus,
    Evidence,
    OutreachDraft,
    PolicyDecision,
    Reply,
    ShareConsent,
)
from bluewatch.outreach import drafts, policy
from bluewatch.outreach.addresses import EMAIL_RE, domain_of
from bluewatch.outreach.senders import FileOutbox, OutboundMessage, SendRefused
from bluewatch.outreach.suppression import Suppression
from bluewatch.outreach.templates import SenderIdentity, simulated_answer
from bluewatch.store import Store

DRAFT_KIND, COMPANY_KIND, EVIDENCE_KIND = "outreach_draft", "outreach_company", "outreach_evidence"
REPLY_KIND, CONSENT_KIND = "outreach_reply", "outreach_consent"
APPROVAL_TTL = timedelta(hours=24)
PUBLIC_DEMO_NOTE = (
    "Sending is off in this workspace: with sending on, this would go to the company's general address after approval."
)

TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"pending_approval", "blocked_suppressed"}),
    "pending_approval": frozenset({"approved", "rejected", "blocked_suppressed"}),
    "approved": frozenset({"pending_approval", "rejected", "sent", "blocked_demo", "blocked_suppressed"}),
    "sent": frozenset({"replied", "bounced", "opted_out"}),
    # A public demo never sends, so its simulated reply starts from blocked_demo.
    "blocked_demo": frozenset({"replied", "opted_out"}),
    "replied": frozenset({"replied", "opted_out"}),
}
_STOP_RE = re.compile(r"\b(stop|stopp|lopeta)\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+|00|0)\d[\d \-]{6,}\d(?!\w)")


class DeskError(RuntimeError):
    """An action the state machine does not allow; the message says why."""


class ReplyOutcome(NamedTuple):
    reply: Reply
    evidence: list[Evidence]  # the unknowns the reply turned into facts confirmed by the company


class Desk:
    def __init__(
        self,
        store: Store | None = None,
        *,
        sender=None,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store or Store()
        self.sender = sender or FileOutbox()
        self.settings = settings or load_settings()
        self.identity = SenderIdentity.from_env(self.settings)
        self.suppression = Suppression(self.store)
        self._now = clock or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------ reading
    def get(self, draft_id: str) -> OutreachDraft:
        draft = self.store.get(DRAFT_KIND, draft_id, OutreachDraft)
        if draft is None:
            raise DeskError(f"No draft {draft_id}.")
        return draft

    def drafts(self, status: DraftStatus | None = None) -> list[OutreachDraft]:
        return [d for d in self.store.all(DRAFT_KIND, OutreachDraft) if status is None or d.status == status]

    def decision(self, draft_id: str) -> PolicyDecision:
        """Why a draft may or may not go out right now, in plain words (for the approval screen)."""
        return self._evaluate(self.get(draft_id)).decision

    def audit_log(self, draft_id: str) -> list[AuditEvent]:
        return [
            AuditEvent(at=datetime.fromisoformat(at), actor=actor, action=action, detail=detail)
            for at, actor, action, _, detail in self.store.audit_log(draft_id)
        ]

    # ------------------------------------------------------------------ the steps
    def submit(
        self,
        draft: OutreachDraft,
        *,
        company: Company,
        evidence: Iterable[Evidence] = (),
        consent: ShareConsent | None = None,
    ) -> OutreachDraft:
        """Queue a draft for approval. Personal addresses are removed before anything is stored."""
        if draft.status != "draft":
            raise DeskError(f"Only new drafts can be submitted (this one is {draft.status}).")
        needed = self._evidence_ids(draft)
        self.store.put(COMPANY_KIND, company.id, company)
        for item in evidence:
            if item.id in needed:
                self.store.put(EVIDENCE_KIND, item.id, item)
        if consent is not None:
            self.store.put(CONSENT_KIND, draft.id, consent)
        result = policy.evaluate(
            draft,
            company=company,
            suppression=self.suppression,
            settings=self.settings,
            evidence=self._stored_evidence(draft),
            consent=consent,
            identity=self.identity,
        )
        draft = draft.model_copy(update={"channel": result.channel})
        reasons = "; ".join(result.decision.reasons)
        if result.blocked_status == "blocked_suppressed":
            return self._move(draft, "blocked_suppressed", "policy", "submit_blocked", reasons)
        if not result.decision.allowed:
            return self._log(draft, "policy", "submit_blocked", reasons)
        return self._move(draft, "pending_approval", "desk", "submitted", f"route {result.decision.route}; {reasons}")

    def edit(self, draft_id: str, *, editor: str, subject: str | None = None, body: str | None = None) -> OutreachDraft:
        """A person edits the text. An approved draft goes back for approval: the old approval is void."""
        draft = self.get(draft_id)
        if draft.status not in ("draft", "pending_approval", "approved"):
            raise DeskError(f"A {draft.status} draft can no longer be edited.")
        draft = draft.model_copy(update={"subject": subject or draft.subject, "body": body or draft.body})
        if draft.status == "approved":
            return self._void(draft, editor, "edited after approval")
        return self._log(draft, editor, "edited", f"text {drafts.text_hash(draft)[:12]}")

    def approve(self, draft_id: str, approver: str, text_hash: str) -> OutreachDraft:
        """Approve the exact text the approver saw (its hash). One draft at a time, never in bulk."""
        draft = self.get(draft_id)
        if draft.status != "pending_approval":
            raise DeskError(f"Only drafts waiting for approval can be approved (this one is {draft.status}).")
        if not approver.strip():
            raise DeskError("An approval needs the approver's name or handle.")
        current = drafts.text_hash(draft)
        if text_hash != current:
            self._log(draft, approver, "approval_refused", "the text changed since it was reviewed")
            raise DeskError("The text changed since you reviewed it. Open it again and approve the new version.")
        result = self._evaluate(draft)
        reasons = "; ".join(result.decision.reasons)
        if result.blocked_status == "blocked_suppressed":
            return self._move(draft, "blocked_suppressed", "policy", "approval_blocked", reasons)
        if not result.decision.allowed:
            return self._log(draft, "policy", "approval_blocked", reasons)
        detail = f"route {result.decision.route}; text {current[:12]}"
        return self._move(
            draft,
            "approved",
            approver,
            "approved",
            detail,
            approver=approver,
            approved_at=self._now(),
            approved_text_hash=current,
            lawful_route=result.decision.route,
        )

    def reject(self, draft_id: str, approver: str, reason: str = "") -> OutreachDraft:
        draft = self.get(draft_id)
        if draft.status not in ("pending_approval", "approved"):
            raise DeskError(f"A {draft.status} draft cannot be rejected.")
        return self._move(draft, "rejected", approver, "rejected", reason)

    def send(self, draft_id: str) -> OutreachDraft:
        draft = self.get(draft_id)
        if draft.status != "approved":
            raise DeskError(f"Nothing is sent without an approval (this draft is {draft.status}).")
        if drafts.text_hash(draft) != draft.approved_text_hash:
            return self._void(draft, "desk", "the text changed after approval; nothing was sent")
        if draft.approved_at is None or self._now() - draft.approved_at > APPROVAL_TTL:
            return self._void(draft, "desk", "the approval expired after 24 hours; nothing was sent")
        if self.settings.public_mode:  # the deployed public app: no sender is ever called
            return self._move(draft, "blocked_demo", "desk", "public_demo", PUBLIC_DEMO_NOTE)

        result = self._evaluate(draft)  # second gate: suppression and demo mode, checked again
        reasons = "; ".join(result.decision.reasons)
        if result.blocked_status:
            return self._move(draft, result.blocked_status, "policy", "send_blocked", reasons)
        if not result.decision.allowed:
            return self._void(draft, "policy", reasons)
        company = self._company(draft)
        org = f"{company.names[0] if company.names else company.id} ({draft.channel.kind})"
        from_address = self.settings.smtp_from or self.identity.stop_address
        message = OutboundMessage(
            draft_id=draft.id,
            to=result.demo_recipient,
            subject=draft.subject,
            body=draft.body,
            from_header=f"{self.identity.org} <{from_address}>" if from_address else self.identity.org,
            stop_address=self.identity.stop_address,
            would_have_gone_to=org,
            idempotency_key=f"{draft.id}-{draft.approved_text_hash[:12]}",
        )
        try:
            sent = self.sender.send(message)
        except SendRefused as exc:
            return self._move(draft, "blocked_demo", "sender", "send_refused", str(exc))
        except (smtplib.SMTPException, OSError) as exc:
            self._log(draft, "sender", "send_failed", type(exc).__name__)
            raise DeskError(f"Sending failed ({type(exc).__name__}); the draft stays approved.") from exc
        detail = f"{sent.detail}; with sending on, this would have gone to {org}"
        return self._move(draft, "sent", "sender", "sent", detail, demo_recipient=message.to or "local file outbox")

    def simulate_reply(
        self, draft_id: str, answers: Mapping[str, str] | Sequence[str] | str, *, classification: str | None = None
    ) -> ReplyOutcome:
        """A teammate's reply in the demo. Answers turn the asked unknowns into facts confirmed by the company.

        `answers` maps question evidence ids to answers, lists them in question order, or is free text
        (a STOP reply opts the company out).
        """
        draft = self.get(draft_id)
        if draft.status not in ("sent", "blocked_demo", "replied"):
            raise DeskError(f"Only a sent message can get a reply (this draft is {draft.status}).")
        if isinstance(answers, str):
            kind = classification or ("opt_out" if _STOP_RE.search(answers) else "other")
            by_id: dict[str, str] = {}
        else:
            kind = classification or "answer"
            by_id = (
                dict(answers)
                if isinstance(answers, Mapping)
                else {q.evidence_id: a for q, a in zip(draft.questions, answers, strict=False)}
            )
        now = self._now()
        company = self._company(draft)
        sender_domain = policy.company_domain(company) or domain_of(draft.channel.address) or "unknown"

        confirmed = []
        if kind == "answer":
            for question in draft.questions:
                text = _clean(by_id.get(question.evidence_id, ""))
                if text:
                    confirmed.append(self._confirm(question.evidence_id, text, draft.id, sender_domain, now))
        elif kind in ("opt_out", "bounce"):
            self.suppression.add(
                reason=kind,
                address=draft.channel.address,
                domain=policy.company_domain(company),
                company_id=company.id if kind == "opt_out" else None,
            )
        snippet = {
            "answer": f"answered {len(confirmed)} of {len(draft.questions)} questions",
            "opt_out": "asked us to stop",
            "bounce": "bounced",
        }.get(kind, "other reply")
        reply = Reply(
            draft_id=draft.id,
            received_at=now,
            from_domain=sender_domain,
            classification=kind,
            snippet=snippet,
            confirms_evidence_ids=[e.id for e in confirmed],
        )
        self.store.put(REPLY_KIND, f"{draft.id}@{now.isoformat()}", reply)
        status = {"opt_out": "opted_out", "bounce": "bounced"}.get(kind, "replied")
        detail = snippet + ("; suppression added (hash only)" if kind in ("opt_out", "bounce") else "")
        self._move(draft, status, "reply", f"reply_{kind}", detail)
        return ReplyOutcome(reply, confirmed)

    def simulated_answers(self, draft_id: str) -> dict[str, str]:
        """For the demo's simulated reply: an example answer to each question, by the field it asks about."""
        answers = {}
        for question in self.get(draft_id).questions:
            unknown = self.store.get(EVIDENCE_KIND, question.evidence_id, Evidence)
            answers[question.evidence_id] = simulated_answer(unknown.field if unknown else "")
        return answers

    # ------------------------------------------------------------------ internals
    def _confirm(self, evidence_id: str, text: str, draft_id: str, sender_domain: str, now: datetime) -> Evidence:
        unknown = self.store.get(EVIDENCE_KIND, evidence_id, Evidence)
        if unknown is None:
            raise DeskError(f"The unknown {evidence_id} behind this question is not stored.")
        fact = unknown.model_copy(
            update={
                "state": "fact",
                "claim": text,
                "value": None,
                "quote": None,
                "url": None,
                "tag": "company_reply",
                "source_family": f"company_reply:{sender_domain}",
                "verified_quote": False,
                "first_seen_at": now,
                "retrieved_at": now,
                "basis": None,
                "why_unknown": None,
                "next_check": None,
                "confirmed_by": Confirmation(by="company_reply", at=now, draft_id=draft_id),
            }
        )
        self.store.put(EVIDENCE_KIND, fact.id, fact)
        return fact

    def _evidence_ids(self, draft: OutreachDraft) -> set[str]:
        ids = set(draft.evidence_ids) | {q.evidence_id for q in draft.questions}
        if draft.channel.role_check_evidence_id:
            ids.add(draft.channel.role_check_evidence_id)
        return ids

    def _stored_evidence(self, draft: OutreachDraft) -> list[Evidence]:
        found = (self.store.get(EVIDENCE_KIND, i, Evidence) for i in sorted(self._evidence_ids(draft)))
        return [e for e in found if e is not None]

    def _company(self, draft: OutreachDraft) -> Company:
        company = self.store.get(COMPANY_KIND, draft.company_id or "", Company)
        if company is None:
            raise DeskError(f"The company of draft {draft.id} is not stored.")
        return company

    def _evaluate(self, draft: OutreachDraft) -> policy.PolicyResult:
        return policy.evaluate(
            draft,
            company=self._company(draft),
            suppression=self.suppression,
            settings=self.settings,
            evidence=self._stored_evidence(draft),
            consent=self.store.get(CONSENT_KIND, draft.id, ShareConsent),
            identity=self.identity,
        )

    def _void(self, draft: OutreachDraft, actor: str, why: str) -> OutreachDraft:
        return self._move(
            draft,
            "pending_approval",
            actor,
            "approval_void",
            why,
            approver=None,
            approved_at=None,
            approved_text_hash=None,
            lawful_route=None,
        )

    def _move(
        self, draft: OutreachDraft, status: DraftStatus, actor: str, action: str, detail: str, **updates
    ) -> OutreachDraft:
        if status not in TRANSITIONS.get(draft.status, frozenset()):
            raise DeskError(f"A draft cannot go from {draft.status} to {status}.")
        return self._log(draft.model_copy(update={"status": status, **updates}), actor, action, detail)

    def _log(self, draft: OutreachDraft, actor: str, action: str, detail: str) -> OutreachDraft:
        event = AuditEvent(at=self._now(), actor=actor, action=action, detail=detail)
        draft = draft.model_copy(update={"audit": [*draft.audit, event]})
        self.store.put(DRAFT_KIND, draft.id, draft)
        self.store.audit(actor, action, draft.id, detail)
        return draft


def _clean(answer: str) -> str:
    """A short answer with addresses and phone numbers removed: the desk stores organisations, not people."""
    text = EMAIL_RE.sub("[address removed]", answer.strip())
    return _PHONE_RE.sub("[number removed]", text)[:300]
