"""Alerts: deadlines within 14 and 30 days, and new signals on companies already on the list.

A share issue is founder-sensitive: its alert says so, and A'Pelago mode should not show it.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from bluewatch.models import Alert, Company, Opportunity, Signal
from bluewatch.rules.text import parse_date

LIVE_TIERS = frozenset({"certain", "likely", "possible"})
REGISTRY_COUNTRY = {"prh": "FI", "brreg": "NO", "rik": "EE", "vies": None, "scb": "SE"}
SIGNAL_PRIORITY = {
    "award": "high",
    "open_tender": "high",
    "eu_grant_signed": "high",
    "eu_project": "high",
    "newly_founded": "medium",
    "new_hostname": "medium",
    "share_issue": "medium",
}
SIGNAL_ACTION = {
    "award": "Look for open tenders in the same class (TED) and send the best one",
    "open_tender": "Check whether a listed company has won this class before",
    "eu_grant_signed": "Look at the project partners for a pilot or reference route",
    "eu_project": "Look at the project partners for a pilot or reference route",
    "newly_founded": "Read the company's site, classify it and add it to the 12-week watch window",
    "new_hostname": "Check what the new product hostname serves",
    "share_issue": "Redstone: check the round stage before any outreach",
}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
EVENT_MAX_AGE_DAYS = 90


def alerts(
    signals: list[Signal],
    companies: list[Company],
    opportunities: list[Opportunity],
    *,
    today: date,
    window_days: int = 7,
) -> list[Alert]:
    created = datetime.combine(today, time(0), tzinfo=timezone.utc)
    out = [_deadline_alert(o, today, created) for o in opportunities if _due_soon(o, today)]
    by_signal = {sid: c for c in companies for sid in c.signal_ids}
    by_registry = {(c.registry.country, c.registry.id): c for c in companies if c.registry.id}
    since = today - timedelta(days=window_days)
    for s in signals:
        company = by_signal.get(s.id) or by_registry.get(
            (REGISTRY_COUNTRY.get(s.entity_ref.registry or ""), s.entity_ref.id)
        )
        if company is None or not _is_new(s, since, today):
            continue
        out.append(_signal_alert(s, company, created))
    out.sort(key=lambda a: (PRIORITY_ORDER[a.priority], a.deadline or date.max, a.id))
    return out


def _due_soon(o: Opportunity, today: date) -> bool:
    return o.tier in LIVE_TIERS and o.deadline is not None and 0 <= (o.deadline - today).days <= 30


def _deadline_alert(o: Opportunity, today: date, created: datetime) -> Alert:
    days = (o.deadline - today).days
    return Alert(
        id=f"deadline:{o.id}",
        company_id=o.company_id,
        trigger="deadline_14d" if days <= 14 else "deadline_30d",
        priority="high" if days <= 14 else "medium",
        reasons=[f"{o.title}: {o.tier} ({o.rule})", deadline_reason(o.deadline, days)],
        evidence_ids=o.evidence_ids,
        next_action=o.action,
        deadline=o.deadline,
        created_at=created,
        opportunity_id=o.id,
        title=o.title,
    )


def deadline_reason(deadline: date, days: int) -> str:
    """'Deadline 31 Oct 2026, in 13 days', with 'today' and 'tomorrow' for the last two days."""
    when = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
    return f"Deadline {deadline:%d %b %Y}, {when}"


def _is_new(s: Signal, since: date, today: date) -> bool:
    """Seen for the first time in the window, about an event that is itself recent: an award from
    last year that a backfill found today is history, not news."""
    first_seen = since <= s.first_seen_at.date() <= today
    recent_event = s.event_date is None or (today - s.event_date).days <= EVENT_MAX_AGE_DAYS
    return first_seen and recent_event


def _signal_alert(s: Signal, company: Company, created: datetime) -> Alert:
    when = f"event {s.event_date:%d %b %Y}" if s.event_date else "undated event"
    title = s.title or s.type.replace("_", " ")
    reasons = [f"{company.names[0]}: {title}", f"{s.source.upper()}, {when}"]
    if s.sensitivity == "founder_sensitive":
        reasons.append("Founder-sensitive signal: Redstone mode only")
    return Alert(
        id=f"signal:{s.id}",
        company_id=company.id,
        trigger=f"new_{s.type}",
        priority=SIGNAL_PRIORITY.get(s.type, "low"),
        reasons=reasons,
        next_action=SIGNAL_ACTION.get(s.type, "Review the new signal"),
        deadline=parse_date(str(s.payload.get("deadline", ""))),
        created_at=created,
        title=title,
    )
