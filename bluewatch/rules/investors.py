"""Investor matching from investors.json: a prioritised list with the parts behind each score.

Parts: stage (the investor's stages against the company's investment readiness and age), thesis
(topic overlap with the company and the preset), geography (national > Nordic > European > global),
ticket, and verification (read > read+snippet > snippet > name-only). Rows marked
exclude_from_matching are never matched. Angel networks are matched as organisations. An investor that
already holds the company is shown as that relationship, and a company past the stage window is no
investor's lead.
"""

from __future__ import annotations

import re
from datetime import date
from functools import lru_cache

from bluewatch import seed
from bluewatch.config import settings
from bluewatch.models import Assessment, Company, Investor, InvestorMatch, Mode
from bluewatch.rules.fit import past_window
from bluewatch.rules.geo import BALTIC, EUROPE, NORDIC, countries_named, country_code
from bluewatch.rules.presets import Preset, load_preset
from bluewatch.rules.text import find_phrases, humanise_keys, slug, trunc, years_between
from bluewatch.rules.topics import shared_topics, topics_of

STAGE_IRL: tuple[tuple[str, tuple[int, int]], ...] = (
    (r"\bidea\b", (1, 3)),
    (r"\bday-0\b", (2, 4)),
    (r"\bpre-seed\b", (3, 6)),
    (r"(?<!pre-)\bseed\b", (5, 8)),
    (r"\bseries[- ]a\b", (8, 9)),
    (r"\bseries[- ][b-f]\b|\blate-stage\b|\bgrowth\b|\bscale-up\b", (9, 9)),
    (r"\bearly-stage\b|\bearly-phase\b|\bstartup\b|\bfeasibility\b|\bpilot\b", (3, 7)),
    (r"\bsme\b|first check to global scale|idea stage onward", (1, 9)),
)
VERIFICATION = {"read": 1.0, "read+snippet": 0.8, "snippet": 0.5, "name-only": 0.2}
GENERALIST = (
    "sector-agnostic",
    "generalist",
    "not stated",
    "no general sector focus",
    "no sector focus",
    "exceptional growth potential",
    "syndicated",
)
NOT_PORTFOLIO = (
    "adjacency only",
    "not a portfolio",
    "none confirmed",
    "example only",
    "underlying funds",
    "investment not confirmed",
)
WHEN_ORDER = {"now": 0, "later": 1, "not_a_fit": 2}
EQUITY_KINDS = frozenset({"vc", "cvc", "impact_fund", "angel_network", "other"})
# A company tag that says which investor already holds it (the research pack tags Redstone Blue's portfolio).
HELD_BY_TAG = {"redstone_portfolio": "redstone-blue"}
HELD = "Already in its portfolio: an existing relationship, not a new lead"


@lru_cache(maxsize=1)
def _rows() -> tuple[tuple[Investor, str], ...]:
    """Each investor with its raw geography text (the contract model has no field for it)."""
    out, seen = [], set()
    for row in seed.load("investors")["investors"]:
        base = slug(row["name"].split(" (")[0])
        iid = base if base not in seen else f"{base}-2"
        seen.add(iid)
        investor = Investor(
            id=iid,
            name=row["name"],
            type=row["type"],
            hq_country=country_code(row.get("hq_country")),
            stages=row.get("stages") or [],
            ticket_eur_min=row.get("ticket_eur_min"),
            ticket_eur_max=row.get("ticket_eur_max"),
            thesis_keywords=row.get("thesis_keywords") or [],
            ocean_portfolio=row.get("ocean_or_maritime_portfolio") or [],
            website=row.get("website"),
            source_urls=row.get("source_urls") or [],
            verification=row.get("verification") or "name-only",
            exclude_from_matching=bool(row.get("exclude_from_matching")),
            status=row.get("status"),
            kind=_kind(row["type"]),
        )
        out.append((investor, row.get("geography") or ""))
    return tuple(out)


def load_investors() -> list[Investor]:
    return [investor for investor, _ in _rows()]


def match(
    company: Company,
    assessment: Assessment,
    *,
    mode: Mode,
    preset: str = "blue",
    limit: int = 12,
    today: date | None = None,
) -> list[InvestorMatch]:
    p = load_preset(preset)
    today = today or settings().today
    irl = next((lv.level for lv in assessment.levels if lv.key == "irl"), None)
    age = years_between(company.registry.founded, today) if company.registry.founded else None
    topics = topics_of(
        " ".join(
            [
                *company.names,
                company.one_liner or "",
                company.vertical_note or "",
                (company.vertical or "").replace("_", " "),
            ]
        )
    )
    country = company.registry.country if company.registry.country != "XX" else None
    service = "no_technology_readiness" in assessment.flags
    late = past_window(assessment)
    held = {inv.id for inv, _ in _rows() if _holds(inv, company)}
    matches = [
        _match(
            inv,
            geo,
            irl,
            age,
            topics,
            country,
            service,
            p,
            mode,
            HELD if inv.id in held else late,
        )
        for inv, geo in _rows()
        if not inv.exclude_from_matching
    ]
    matches.sort(key=lambda m: (WHEN_ORDER[m.when], -m.score, m.investor_id))
    ranked = [m.model_copy(update={"rank": i + 1}) for i, m in enumerate(matches)]
    # Always shown: the company's existing investors, and in Redstone mode its own fund.
    always = held | ({p.house_fund.investor_id} if mode == "redstone" and p.house_fund else set())
    return ranked[:limit] + [m for m in ranked[limit:] if m.investor_id in always]


def _holds(inv: Investor, company: Company) -> bool:
    """Whether the investor already holds the company: by the pack's tag, or by name in its portfolio list."""
    if any(tag in company.tags and HELD_BY_TAG[tag] == inv.id for tag in HELD_BY_TAG):
        return True
    held = {slug(x.split(" (")[0]) for x in inv.ocean_portfolio if not any(w in x.lower() for w in NOT_PORTFOLIO)}
    names = {slug(n) for n in company.names}
    return any(n == h or n.startswith(f"{h}-") for n in names for h in held)


def _match(
    inv: Investor,
    geography: str,
    irl: int | None,
    age: float | None,
    topics: set[str],
    country: str | None,
    service: bool,
    p: Preset,
    mode: Mode,
    closed: str | None,
) -> InvestorMatch:
    """`closed` is the label when the company can be no lead for this investor whatever the fit parts say."""
    stage, stage_why = _stage(inv, irl, age, p)
    thesis, thesis_why, shared = _thesis(inv, topics, p)
    geo, geo_label = _geography(geography, country)
    ticket = _ticket(inv, irl)
    verification = VERIFICATION.get(inv.verification, 0.2)
    weights = p.weights.investor
    parts = {"stage": stage, "thesis": thesis, "geography": geo, "ticket": ticket, "verification": verification}
    score = round(sum(weights[k] * v for k, v in parts.items()), 4)
    status = (inv.status or "").lower()
    paused = "paused" in status or status.startswith("closed")

    caveats = []
    if paused:
        caveats.append(f"Status: {inv.status}")
    if inv.verification in ("snippet", "name-only"):
        caveats.append(f"Verification: {inv.verification} (figures unconfirmed)")
    if inv.ticket_eur_min is None and inv.ticket_eur_max is None:
        caveats.append("Ticket not stated")
    if not _stage_range(inv.stages):
        caveats.append("Stages not stated")

    if closed:
        when, label = "not_a_fit", closed
    elif geo == 0.0 or thesis <= 0.1 or stage == 0.0:
        when = "not_a_fit"
        why_not = "outside its geography" if geo == 0.0 else "thesis does not match" if thesis <= 0.1 else stage_why
        label = f"Not now: {why_not}"
    elif not topics:
        # Register facts alone do not say what a company does, so no thesis, not even a generalist's, can be
        # judged a fit yet.
        when, label = "later", "Partial fit: what the company does is not known yet"
    elif service and inv.kind in EQUITY_KINDS:
        when, label = "later", "Partial fit: a service business, not a venture investment case yet"
    elif stage >= 0.75 and thesis >= 0.4 and geo >= 0.5 and verification >= 0.5 and not paused:
        when = "now"
        label = "Fit: " + ", ".join(["stage", *(sorted(shared)[:2] or ["generalist"]), geo_label])
    else:
        when = "later"
        if paused:
            label = f"Partial fit: status {inv.status}"
        elif stage < 0.75:
            label = f"Partial fit: {stage_why}"
        else:
            label = "Partial fit: " + ("verification is thin" if verification < 0.5 else "thesis is general")
    if mode == "redstone" and p.house_fund and inv.id == p.house_fund.investor_id:
        label = f"{p.house_fund.label}: {label}"

    why = [stage_why, thesis_why, f"Geography: {geography or 'not stated'} ({geo_label})"]
    if inv.ticket_eur_min or inv.ticket_eur_max:
        why.append(f"Ticket EUR {inv.ticket_eur_min or '?'}-{inv.ticket_eur_max or '?'}")
    portfolio = [x for x in inv.ocean_portfolio if not any(w in x.lower() for w in NOT_PORTFOLIO)]
    if portfolio:
        why.append(f"Ocean portfolio: {', '.join(portfolio[:3])}")
    if inv.kind == "angel_network":
        why.append("An angel network: approach the network as an organisation, never individual angels")
    return InvestorMatch(
        investor_id=inv.id,
        name=inv.name,
        rank=0,
        score=score,
        parts={k: round(v, 3) for k, v in parts.items()},
        fit_label=humanise_keys(label),
        why=[humanise_keys(line) for line in why],
        caveats=caveats,
        verification=inv.verification,
        when=when,
    )


def _stage_range(stages: list[str]) -> tuple[int, int] | None:
    found = _stage_matches(stages)
    return (min(r[0] for r in found), max(r[1] for r in found)) if found else None


def _stage_matches(stages: list[str]) -> list[tuple[int, int]]:
    text = " ".join(stages).lower()
    return [rng for pattern, rng in STAGE_IRL if re.search(pattern, text)]


def _stage(inv: Investor, irl: int | None, age: float | None, p: Preset) -> tuple[float, str]:
    rng = _stage_range(inv.stages)
    if rng is None:
        return 0.5, "Investment stages not stated"
    lo, hi = rng
    stages = ", ".join(inv.stages)
    # An older company is past an early-stage investor's window even when its readiness evidence is thin;
    # only investors that also do growth or late stage stay open to it.
    if age is not None and age >= p.stage_window.max_age_years and (9, 9) not in _stage_matches(inv.stages):
        return 0.0, f"Invests at {stages}; the company is {trunc(age, 0)} years old, past that window"
    if irl is None:
        return 0.5, f"Invests at {stages}; the company's investment readiness is unknown"
    if lo <= irl <= hi:
        return 1.0, f"Invests at {stages}; the company is at IRL {irl}"
    if irl < lo:
        return round(max(0.2, 1 - 0.2 * (lo - irl)), 2), f"Invests at {stages}; the company (IRL {irl}) is earlier"
    return 0.0, f"Invests at {stages}; the company (IRL {irl}) is past that stage"


def _thesis(inv: Investor, topics: set[str], p: Preset) -> tuple[float, str, set[str]]:
    portfolio = [x for x in inv.ocean_portfolio if not any(w in x.lower() for w in NOT_PORTFOLIO)]
    text = " ".join([*inv.thesis_keywords, inv.type, "ocean" if portfolio else ""])
    keywords = ", ".join(inv.thesis_keywords[:4]) or "not stated"
    if not topics:
        return 0.5, f"Thesis: {keywords} (what the company does is not known yet)", set()
    if not topics_of(text) or find_phrases(" ".join(inv.thesis_keywords), GENERALIST):
        return 0.4, f"Thesis: {keywords} (generalist or not stated)", set()
    shared = shared_topics(text, topics)
    preset_fit = shared_topics(text, set(p.investor_topics))
    note = f"Thesis: {keywords}" + (f" (shared: {', '.join(sorted(shared))})" if shared else " (no overlap)")
    if not shared:
        return 0.1, note, shared
    value = 1.0 if len(shared) >= 2 or preset_fit else 0.75
    return value, note, shared


def _geography(text: str, country: str | None) -> tuple[float, str]:
    lower = text.lower()
    if not text or lower.startswith("not stated"):
        return 0.5, "geography not stated"
    if country is None:
        return 0.5, "company country unknown"
    named = countries_named(text)
    # Order matters: "Nordic SMEs; green solutions in global markets" is a Nordic investor.
    if re.search(r"\bnordics?\b|northern europe", lower):
        scope, label, value = NORDIC | BALTIC | named, "Nordic", 0.85
    elif re.search(r"\bglobal\b|\bworldwide\b|europe and beyond", lower):
        scope, label, value = None, "global", 0.6
    elif re.search(r"\b(pan-)?europe(an)?\b", lower):
        scope, label, value = EUROPE | named | ({"US"} if re.search(r"\bus\b", lower) else set()), "European", 0.7
    elif named == {country}:
        scope, label, value = named, "national", 1.0
    elif named:
        scope, label, value = named, "Nordic" if named <= NORDIC | BALTIC else "regional", 0.85
    else:
        return 0.5, "geography not machine-readable"
    if scope is not None and country not in scope:
        return 0.0, "outside its geography"
    return value, label


def _ticket(inv: Investor, irl: int | None) -> float:
    if inv.ticket_eur_min is None and inv.ticket_eur_max is None:
        return 0.5
    level = irl or 3
    round_lo, round_hi = (
        (50_000, 500_000)
        if level <= 4
        else (100_000, 1_000_000)
        if level <= 6
        else (500_000, 3_000_000)
        if level == 7
        else (1_000_000, 10_000_000)
        if level == 8
        else (5_000_000, 50_000_000)
    )
    lo, hi = inv.ticket_eur_min or 0, inv.ticket_eur_max or 10**9
    return 1.0 if lo <= round_hi and round_lo <= hi else 0.2


def _kind(investor_type: str) -> str:
    t = investor_type.lower()
    if "angel" in t:
        return "angel_network"
    if "cvc" in t:
        return "cvc"
    if t.startswith("public"):
        return "public"
    if "impact" in t:
        return "impact_fund"
    if "accelerator" in t:
        return "accelerator"
    if re.search(r"\bvc\b|venture|deep-tech investor", t):
        return "vc"
    return "other"
