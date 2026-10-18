"""The outreach policy: may this draft go out, by which lawful route, and to which inbox in demo mode.

Code, not a prompt, so the rules are testable and cannot be talked around. The desk runs it at submit, at
approval and again at send.
The channel ladder, in order of preference:

1. org_generic, org_press, contact_form: the organisation's own general address, press contact or form.
   Lawful for companies unless they opt out (Act 917/2014 §202).
2. named_role: a founder or CEO role address, only with a stored role check (the Data Protection
   Ombudsman's "authorisation by role").
3. opt_in: only with a recorded consent that has not been withdrawn (§200).
X. personal_blocked: personal or scraped addresses. Blocked; the address is never stored.

Only companies matched to the register as "resolved" can be contacted, so a namesake (Seaber vs
Seaberry) can never get the message. Demo mode is the only mode this build has: every message goes to
our own team inbox from OUTREACH_ALLOWLIST, or only to the local file outbox when none is set.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from bluewatch.config import Settings
from bluewatch.models import Channel, Company, DraftStatus, Evidence, OutreachDraft, PolicyDecision, ShareConsent
from bluewatch.outreach.addresses import EMAIL_RE, domain_of, on_domain, sanitise
from bluewatch.outreach.suppression import Suppression
from bluewatch.outreach.templates import LANGUAGES, SenderIdentity, footer_problems

ROUTES = {
    "org_generic": "org_generic",
    "org_press": "org_generic",
    "contact_form": "org_generic",
    "named_role": "role_authorised",
    "opt_in": "consent",
}


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    channel: Channel  # what may be stored: personal addresses already removed
    blocked_status: DraftStatus | None  # blocked_suppressed / blocked_demo, or None
    demo_recipient: str | None  # our team inbox; None means the local file outbox only


def company_domain(company: Company) -> str | None:
    return domain_of(company.domain) or domain_of(company.registry.website)


def demo_recipient(settings: Settings) -> str | None:
    return settings.outreach_allowlist[0] if settings.outreach_allowlist else None


def decide(
    draft: OutreachDraft,
    *,
    company: Company,
    suppression: Suppression | None,
    settings: Settings,
    evidence: Iterable[Evidence] | None = None,
    consent: ShareConsent | None = None,
    identity: SenderIdentity | None = None,
) -> PolicyDecision:
    return evaluate(
        draft,
        company=company,
        suppression=suppression,
        settings=settings,
        evidence=evidence,
        consent=consent,
        identity=identity,
    ).decision


def evaluate(
    draft: OutreachDraft,
    *,
    company: Company,
    suppression: Suppression | None,
    settings: Settings,
    evidence: Iterable[Evidence] | None = None,
    consent: ShareConsent | None = None,
    identity: SenderIdentity | None = None,
) -> PolicyResult:
    identity = identity or SenderIdentity.from_env(settings)
    known = None if evidence is None else {e.id: e for e in evidence}
    domain = company_domain(company)
    channel = sanitise(draft.channel, company_domain=domain)
    demo = settings.outreach_mode == "demo"

    blocks = _company_problems(draft, company)
    channel_blocks, notes = _channel_check(channel, company, domain, demo, known, consent)
    blocks += channel_blocks + _content_problems(draft, company, identity, known)

    suppressed = bool(
        suppression and suppression.matches(address=channel.address, domain=domain, company_id=company.id)
    )
    if suppressed:
        blocks.append(f"{_name(company)} asked us to stop: it is on the suppression list.")
    if not demo:
        blocks.append("Sending is off in this workspace.")

    recipient = demo_recipient(settings)
    if demo and settings.public_mode:
        notes.append("Sending is off in this workspace: nothing is sent to the company or anyone else.")
    elif demo:
        where = f"our team inbox {recipient}" if recipient else "the local file outbox only (no e-mail)"
        notes.append(f"Sending goes to {where} only, never to {_name(company)}.")
    status: DraftStatus | None = "blocked_suppressed" if suppressed else (None if demo else "blocked_demo")
    decision = PolicyDecision(allowed=not blocks, route=ROUTES.get(channel.kind), reasons=blocks or notes)
    return PolicyResult(decision=decision, channel=channel, blocked_status=status, demo_recipient=recipient)


def _name(company: Company) -> str:
    return company.names[0] if company.names else company.id


def _company_problems(draft: OutreachDraft, company: Company) -> list[str]:
    problems = []
    if draft.company_id != company.id:
        problems.append("The draft belongs to another company.")
    if company.resolution.state != "resolved":
        problems.append(
            f"{_name(company)} is only '{company.resolution.state}' in the register match. Confirm the "
            "company first, so the message cannot reach a namesake."
        )
    if company.registry.natural_person:
        problems.append("Sole traders are natural persons and are never contacted.")
    return problems


def _channel_check(
    channel: Channel,
    company: Company,
    domain: str | None,
    demo: bool,
    known: dict[str, Evidence] | None,
    consent: ShareConsent | None,
) -> tuple[list[str], list[str]]:
    """(blocking reasons, explanations) for the channel ladder."""
    kind = channel.kind
    if kind == "personal_blocked":
        return ["Personal or scraped addresses are blocked in code, and the address is not stored."], []
    blocks, notes = [], []
    if channel.address is None:
        if demo:
            notes.append(
                "No published organisation address is on file. That is fine while sending is off, but a "
                "real send needs the company's own general address."
            )
        else:
            blocks.append("No organisation address is on file.")
    elif domain is None:
        blocks.append("The company's own domain is unknown, so the address cannot be confirmed as its own.")
    elif not on_domain(domain_of(channel.address), domain):
        blocks.append(f"The address is not on the company's own domain ({domain}).")

    if kind in ("org_generic", "org_press", "contact_form"):
        notes.append(
            "The organisation's general address: allowed for companies unless they opt out (Act 917/2014 §202)."
        )
    elif kind == "named_role":
        blocks += _role_check_problems(channel, known)
        notes.append(
            "Named role: allowed only because the role is checked and tied to the offer. Never "
            "automated: each one is approved on its own."
        )
    elif kind == "opt_in":
        if consent is None or not consent.given or consent.withdrawn_at is not None:
            blocks.append("Opt-in needs a recorded consent that has not been withdrawn.")
        else:
            notes.append("Opt-in: the company gave its consent.")
    return blocks, notes


def _role_check_problems(channel: Channel, known: dict[str, Evidence] | None) -> list[str]:
    if not channel.role_check_evidence_id:
        return ["A named role needs a stored role check (a public source showing the founder or CEO role)."]
    if known is None:
        return ["The role check could not be verified: no stored evidence was given."]
    check = known.get(channel.role_check_evidence_id)
    if check is None or check.state != "fact" or not check.url:
        return ["The role check is missing or is not a sourced fact."]
    return []


def _content_problems(
    draft: OutreachDraft, company: Company, identity: SenderIdentity, known: dict[str, Evidence] | None
) -> list[str]:
    problems = []
    if draft.language not in LANGUAGES:
        problems.append(f"There is no template for language '{draft.language}'.")
    if not draft.subject.strip():
        problems.append("The subject is empty.")
    if not (draft.bridge_id or draft.opportunity_ref):
        problems.append("Every first message must offer one useful opportunity.")
    if draft.mode == "evidence_request" and not 1 <= len(draft.questions) <= 2:
        problems.append("An evidence request asks one or two questions.")
    for question in draft.questions:
        if question.evidence_id not in draft.evidence_ids:
            problems.append("A question is not linked to the draft's evidence.")
        elif known is not None and (
            known.get(question.evidence_id) is None or known[question.evidence_id].state != "unknown"
        ):
            problems.append(f"Question '{question.text[:40]}...' does not close a stored unknown.")
    problems += footer_problems(draft.body, draft.language, identity, _name(company))
    foreign = {a.lower() for a in EMAIL_RE.findall(draft.body)} - {(identity.stop_address or "").lower()}
    if foreign:
        problems.append("The text contains an e-mail address that is not our stop address.")
    return problems
