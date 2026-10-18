"""The weekly shortlist: at most `cap` rows, never padded, each with a reason to be there this week.

A row qualifies when it is newly founded, newly active (a dated signal), or promising and new to
your list. Its rank is the sum of its rank_parts (weighted fit, signal, group, evidence and
potential), so the order can be recomputed from the numbers shown.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone

from bluewatch.config import settings
from bluewatch.labels import LIST_NAME, SOURCE_LABELS
from bluewatch.models import (
    Assessment,
    Chip,
    Company,
    Evidence,
    ListEntry,
    Mode,
    Reason,
    ShortList,
    Signal,
    SourceStatus,
)
from bluewatch.rules import gaps
from bluewatch.rules.evidence import facts, field_of, is_none_found
from bluewatch.rules.fit import founded_on
from bluewatch.rules.presets import Preset, load_preset
from bluewatch.rules.text import parse_date
from bluewatch.rules.version import rules_version

Item = tuple[Company, Assessment, list[Evidence], list[Signal]]

CHIP_SIGNAL = {"newly_founded": 1.0, "newly_active": 0.8, "new_to_list": 0.4}
GROUP_VALUE = {"act_now": 1.0, "dive_deeper": 0.8, "not_yet": 0.3}
ACTIVE_TYPES = {"award", "share_issue", "eu_project", "eu_grant_signed", "new_hostname"}
# Founders find share issues intrusive, so A'Pelago mode never surfaces a row on one.
APELAGO_ACTIVE = {"award", "eu_project", "eu_grant_signed", "new_hostname"}
LIST_TAG = {"apelago": "apelago_cohort", "redstone": "redstone_portfolio"}
REASON_FIELDS = (
    "public_contracts",
    "customers",
    "pilot",
    "programme",
    "grant",
    "funding",
    "award",
    "identity",
    "market",
    "deployment",
    "certification",
)
SIGNAL_FIELD = {"award": "public_contracts", "share_issue": "funding", "new_hostname": "product"}


@dataclass
class _Row:
    company: Company
    assessment: Assessment
    evidence: list[Evidence]
    signals: list[Signal]
    chip: Chip
    chip_signal: Signal | None
    parts: dict[str, float]

    @property
    def total(self) -> float:
        return self.parts["total"]


def shortlist(
    items: list[Item],
    *,
    mode: Mode,
    preset: str = "blue",
    cap: int = 10,
    since: datetime | None = None,
    sources: tuple[SourceStatus, ...] | list[SourceStatus] = (),
    today: date | None = None,
) -> ShortList:
    p = load_preset(preset)
    today = today or settings().today
    rows: list[_Row] = []
    skipped: Counter[str] = Counter()
    for item in items:
        row = _qualify(item, mode, p, today)
        if isinstance(row, str):
            skipped[row] += 1
        else:
            rows.append(row)
    ranked = sorted(rows, key=lambda r: (-r.total, r.company.id))
    entries = [_entry(i + 1, row, mode, p, today, since) for i, row in enumerate(ranked[:cap])]
    return ShortList(
        mode=mode,
        preset=p.name,
        generated_at=datetime.now(timezone.utc),
        entries=entries,
        cap=cap,
        why_these=_why_these(entries, len(items), len(ranked), mode, p),
        why_not_next=_why_not_next(ranked, cap, skipped),
        since=since,
        sources=list(sources),
        rules_version=rules_version(),
    )


def _qualify(item: Item, mode: Mode, p: Preset, today: date) -> _Row | str:
    """A qualifying row, or the reason it was left out."""
    company, assessment, evidence, signals = item
    if company.registry.natural_person:
        return "sole traders (private persons, never ranked)"
    if assessment.score.group == "not_for_us":
        return "not for us (off-thesis or too late)"
    if LIST_TAG[mode] in company.tags:
        return "already in your list"
    chip, chip_signal = _chip(company, assessment, evidence, signals, mode, p, today)
    if chip is None:
        return "no new reason this week"
    if not _reason_facts(evidence, chip, chip_signal, mode):
        return "no sourced reason to show in this mode"
    weights = p.weights.rank
    values = {
        "fit": assessment.score.potential_parts.get("thesis_fit", 0.0),
        "signal": CHIP_SIGNAL[chip],
        "group": GROUP_VALUE[assessment.score.group],
        "evidence": assessment.score.evidence,
        "potential": assessment.score.potential,
    }
    parts = {k: round(weights[k] * v, 4) for k, v in values.items()}
    parts["total"] = round(sum(parts.values()), 4)
    return _Row(company, assessment, evidence, signals, chip, chip_signal, parts)


def _chip(
    company: Company,
    assessment: Assessment,
    evidence: list[Evidence],
    signals: list[Signal],
    mode: Mode,
    p: Preset,
    today: date,
) -> tuple[Chip | None, Signal | None]:
    founded = founded_on(company, evidence)
    if founded and 0 <= (today - founded).days <= p.windows.newborn_weeks * 7:
        return "newly_founded", None
    allowed = APELAGO_ACTIVE if mode == "apelago" else ACTIVE_TYPES
    recent = [
        s
        for s in signals
        if s.type in allowed and s.event_date and 0 <= (today - s.event_date).days <= p.windows.newly_active_days
    ]
    if recent:
        return "newly_active", max(recent, key=lambda s: (s.event_date, s.id))
    if assessment.score.group in ("act_now", "dive_deeper"):
        return "new_to_list", None
    return None, None


def _entry(rank: int, row: _Row, mode: Mode, p: Preset, today: date, since: datetime | None) -> ListEntry:
    c = row.company
    return ListEntry(
        rank=rank,
        company_id=c.id,
        name=c.names[0],
        country=c.registry.country,
        founded=founded_on(c, row.evidence),
        vertical=c.vertical,
        vertical_note=c.vertical_note,
        chip=row.chip,
        group=row.assessment.score.group,
        reasons=_reasons(row, mode),
        next_action=_next_action(row, mode),
        deadline=_deadline(row.signals, today),
        change=_change(row, since),
        modes=[
            m
            for m in ("apelago", "redstone")
            if not isinstance(_qualify((c, row.assessment, row.evidence, row.signals), m, p, today), str)
        ],
        score=row.assessment.score,
        rank_parts=row.parts,
    )


def _reasons(row: _Row, mode: Mode) -> list[Reason]:
    return [_reason(e) for e in _reason_facts(row.evidence, row.chip, row.chip_signal, mode)]


def _reason_facts(evidence: list[Evidence], chip: Chip, chip_signal: Signal | None, mode: Mode) -> list[Evidence]:
    """Up to three sourced facts: why now, what it does, the strongest proof."""
    usable = [e for e in facts(evidence) if not is_none_found(e)]
    if mode == "apelago":
        usable = [e for e in usable if not (field_of(e) == "funding" and e.source_family == "prh_notices")]
    picked: list[Evidence] = []
    if chip == "newly_founded":
        picked += [e for e in usable if field_of(e) == "founded"][:1]
    elif chip == "newly_active" and chip_signal:
        target = SIGNAL_FIELD.get(chip_signal.type)
        picked += [e for e in usable if field_of(e) == target and e.event_date == chip_signal.event_date][:1]
    picked += [e for e in usable if field_of(e) == "product" and e.source_family != "crtsh" and e not in picked][:1]
    for wanted in REASON_FIELDS:
        if len(picked) >= 3:
            break
        picked += [e for e in usable if field_of(e) == wanted and e not in picked][:1]
    return picked[:3]


def _reason(e: Evidence) -> Reason:
    return Reason(
        text=e.claim,
        evidence_id=e.id,
        source_label=source_label(e.source_family),
        url=e.url,
        event_date=e.event_date,
        first_seen_at=e.first_seen_at,
        retrieved_at=e.retrieved_at,
    )


def source_label(family: str) -> str:
    if family in SOURCE_LABELS:
        return SOURCE_LABELS[family]
    if family.startswith("site:"):
        return f"Company site ({family.removeprefix('site:')})"
    return {
        "prh_notices": "Finland trade register notices (PRH)",
        "crtsh": "Certificate transparency logs (crt.sh)",
        "research_pack": "Research pack (pages read 16-17 Oct 2026)",
        "regulation": "EU regulation (read in the research dossier)",
        "gap_ledger": "Gap ledger",
    }.get(family, family)


def _next_action(row: _Row, mode: Mode) -> str:
    group = row.assessment.score.group
    prefix = "Redstone: " if mode == "redstone" else ""
    if group == "not_yet":
        return "Watch: re-check the public site in 4 weeks; no contact yet"
    if group == "dive_deeper":
        ledger = gaps.ledger(row.company, row.evidence)
        questions = [e.next_check.question for e in ledger.unknowns if e.next_check and e.next_check.question]
        if questions:
            return f"{prefix}Ask the company: " + " ".join(questions[:2])
        return f"{prefix}Verify the business before any contact"
    if mode == "redstone":
        return "Redstone: contact now; thesis and window fit, confirm the round stage"
    return "Contact now with the best-fit programme or open call (see the card's opportunities)"


def _deadline(signals: list[Signal], today: date) -> date | None:
    deadlines = [d for s in signals if (d := parse_date(str(s.payload.get("deadline", "")))) and d >= today]
    return min(deadlines, default=None)


def _change(row: _Row, since: datetime | None) -> str | None:
    """What happened after the last digest, from dated facts only: a register date after it means the
    company is new; a signal dated after it is a change. When our pipeline first saw something says nothing
    about the company, so it never counts, and an event dated on the digest day itself is not counted."""
    if since is None:
        return None
    cutoff = since.date()
    founded = founded_on(row.company, row.evidence)
    if founded and founded > cutoff:
        return "new since you last looked"
    newer = sorted({s.title or s.type.replace("_", " ") for s in row.signals if s.event_date and s.event_date > cutoff})
    if newer:
        return "changed: " + "; ".join(newer)
    return None


def _why_these(entries: list[ListEntry], pool: int, qualified: int, mode: Mode, p: Preset) -> str:
    chips = Counter(e.chip for e in entries)
    weights = ", ".join(f"{k} {v:g}" for k, v in p.weights.rank.items())
    workspace = {"apelago": "A'Pelago", "redstone": "Redstone"}[mode]
    return (
        f"Why these {len(entries)}: of {pool} companies, {qualified} qualified in the {workspace} workspace "
        f"with the {p.label} preset ({chips['newly_founded']} newly founded, {chips['newly_active']} newly active, "
        f"{chips['new_to_list']} promising and new to your list are shown). Rank = weighted sum of {weights}. "
        f"{LIST_NAME} caps at the limit; it is never padded."
    )


def _why_not_next(ranked: list[_Row], cap: int, skipped: Counter[str]) -> str:
    left_out = "; ".join(f"{n} {why}" for why, n in skipped.most_common())
    if len(ranked) <= cap:
        rows = "1 row" if len(ranked) == 1 else f"{len(ranked)} rows"
        return f"Only {rows} qualified, so the other slots stay empty. Left out: {left_out}."
    nxt, last = ranked[cap], ranked[cap - 1]
    # Totals carry four decimals (rank_parts), so printing four never rounds one past the other.
    if nxt.total == last.total:
        return (
            f"#{cap + 1} would be {nxt.company.names[0]}, tied with #{cap} {last.company.names[0]} at "
            f"{last.total:.4f}; equal totals are ordered by company ID. Left out: {left_out}."
        )
    gap = max((k for k in last.parts if k != "total"), key=lambda k: last.parts[k] - nxt.parts[k])
    return (
        f"#{cap + 1} would be {nxt.company.names[0]} at {nxt.total:.4f}, below #{cap} "
        f"{last.company.names[0]} at {last.total:.4f}, mostly on {gap}. Left out: {left_out}."
    )
