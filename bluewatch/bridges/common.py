"""Shared helpers for bridges: name keys, dates, evidence grading and the bridge constructor."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date

from bluewatch.config import settings
from bluewatch.models import Bridge, BridgeEvidence, BridgeParty, BridgeType

# Tags that mean "read by us or backed by a register". A company's own site counts as read for
# claims about what the company sells; search snippets, unlinked research notes and model output do not.
STRONG_TAGS = {"read", "registry", "brreg", "prh", "ted", "cordis", "sedia", "site"}

# How well the two sides join, before evidence quality: an exact join (same project, same tender
# class) versus a partial one (same CPV class only) versus an inferred one (fit by rules or keywords).
FIT = {"exact": 1.0, "partial": 0.7, "inferred": 0.4}

_LEGAL_FORMS = {"oy", "oyj", "ab", "as", "asa", "aps", "ou", "uab", "sia", "ehf", "gmbh", "ltd", "sas", "llc", "ag"}
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
# Ordinary words a company name can start with; on their own they don't name the company.
_COMMON_WORDS = {
    "arctic",
    "blue",
    "fish",
    "gate",
    "marine",
    "nova",
    "ocean",
    "organic",
    "origin",
    "seaweed",
    "service",
    "sincere",
    "sub",
    "under",
    "viva",
}


def today_or_default(today: date | None) -> date:
    return today or settings().today


def norm_name(name: str) -> str:
    """Accent-free, lower-case words without legal-form suffixes: 'MarineHäkk' -> 'marinehakk'."""
    ascii_text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return " ".join(w for w in re.findall(r"[a-z0-9]+", ascii_text) if w not in _LEGAL_FORMS)


def naming_words(name: str) -> list[str]:
    """Words that name a company where its full name doesn't appear: the first word of its name and of a
    name in brackets ('Groke' as in 'Groke PRO', 'WAI' from 'WAIing (WAI Water Intelligence)')."""
    words = []
    for part in re.split(r"[()]", name):
        tokens = [t for t in part.split() if t.casefold() not in _LEGAL_FORMS]
        if tokens and len(tokens[0]) >= 3 and tokens[0].casefold() not in _COMMON_WORDS:
            words.append(tokens[0])
    return words


def slug(text: str) -> str:
    return norm_name(text).replace(" ", "-")


def iso_dates(text: str | None) -> list[date]:
    found = []
    for y, m, d in _ISO_DATE.findall(text or ""):
        try:
            found.append(date(int(y), int(m), int(d)))
        except ValueError:
            continue
    return found


def first_iso_date(text: str | None) -> date | None:
    dates = iso_dates(text)
    return dates[0] if dates else None


def fmt_day(d: date) -> str:
    return f"{d.day} {d:%b %Y}"


def fmt_month(d: date) -> str:
    return f"{d:%b %Y}"


def party_key(party: BridgeParty) -> str:
    """The key for_company() matches: the company id, else country:registry id, else the name."""
    if party.company_id:
        return party.company_id
    if party.country and party.registry_id:
        return f"{party.country}:{party.registry_id}"
    return f"name:{norm_name(party.name)}"


def bridge_id(type: BridgeType, company: BridgeParty, counterparty: BridgeParty) -> str:
    """A short id that stays the same while the parties do: 'programme_fit-3f2a91c0'. It goes into links,
    so it is a digest of the parties rather than their register IDs or names."""
    key = f"{type}/{party_key(company)}/{slug(counterparty.name)}"
    return f"{type}-{hashlib.blake2s(key.encode(), digest_size=4).hexdigest()}"


def is_strong(tag: str) -> bool:
    return tag in STRONG_TAGS or tag.startswith("cordis")


def strong_share(bridge: Bridge) -> float:
    items = bridge.evidence_company + bridge.evidence_counterparty
    return sum(is_strong(e.tag) for e in items) / len(items)


def grade(company: list[BridgeEvidence], counterparty: list[BridgeEvidence], join: str) -> str:
    """Verified needs an exact join with every item read or register-backed on both sides."""
    if join == "exact" and all(is_strong(e.tag) for e in company + counterparty):
        return "verified"
    if (
        join in ("exact", "partial")
        and any(is_strong(e.tag) for e in company)
        and any(is_strong(e.tag) for e in counterparty)
    ):
        return "probable"
    return "possible"


def identifying_terms_for(company: BridgeParty, terms: list[str]) -> list[str]:
    """The terms that identify the company side, without repeats: the given ones, plus a company's naming words."""
    words = naming_words(company.name) if company.kind in (None, "company") else []
    return list(dict.fromkeys(t for t in [*terms, *words] if t))


def _has_date(bridge: Bridge) -> bool:
    items = bridge.evidence_company + bridge.evidence_counterparty
    return bridge.deadline is not None or any(e.date or e.deadline or e.end for e in items)


def make_bridge(
    *,
    type: BridgeType,
    company: BridgeParty,
    counterparty: BridgeParty,
    reason: str,
    evidence_company: list[BridgeEvidence],
    evidence_counterparty: list[BridgeEvidence],
    join: str,
    action: str,
    deadline: date | None = None,
    caveat: str | None = None,
    mode: str = "both",
    anonymised_name: str | None = None,
    identifying_terms: list[str] | None = None,
    fit: float | None = None,
) -> Bridge:
    """Build a generated bridge and enforce the rules every bridge must meet. A company's naming words
    join the identifying terms; a research team's name is no help there, so its generator lists them."""
    bridge = Bridge(
        id=bridge_id(type, company, counterparty),
        type=type,
        company=company,
        counterparty=counterparty,
        reason=reason,
        evidence_company=evidence_company,
        evidence_counterparty=evidence_counterparty,
        deadline=deadline,
        action=action,
        confidence=grade(evidence_company, evidence_counterparty, join),
        caveat=caveat,
        mode=mode,
        anonymised_name=anonymised_name,
        identifying_terms=identifying_terms_for(company, identifying_terms or []),
        rank_parts={"fit": fit if fit is not None else FIT[join]},
        generator=type,
    )
    if not (evidence_company and evidence_counterparty):
        raise ValueError(f"{bridge.id}: a bridge needs evidence on both sides")
    if not _has_date(bridge):
        raise ValueError(f"{bridge.id}: a bridge needs a deadline or a dated piece of evidence")
    return bridge
