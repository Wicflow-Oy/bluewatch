"""Next steps for an idea: the one check that would change the read most, then the programmes, proof steps
and funding routes that fit, from data/seed/grants.json.

Instruments are never invented: every route names an id in the seed (tests/ideas checks this), and its
name, status, deadline and source link come from that row. When nothing fits, the read says so.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from bluewatch import seed
from bluewatch.ideas.models import IdeaStep, IdeaSubmission, StepKind
from bluewatch.ideas.rubric import BY_ID, Reading, gap_order
from bluewatch.rules.text import parse_date

MAX_STEPS = 3
OBSERVATION = re.compile(
    r"\b(?:sensors?|monitor\w*|observ\w*|buoys?|underwater|measur\w*|ocean data|sonar|"
    r"water quality)\b",
    re.I,
)
KIND_ORDER: dict[StepKind, int] = {"check": 0, "invite": 1, "programme": 2, "proof_step": 3, "funding": 4}


@dataclass(frozen=True)
class RouteRule:
    instrument_id: str
    kind: StepKind
    presets: tuple[str, ...]
    fits: Callable[[IdeaSubmission, Reading], bool]
    why: str  # who it is for, summarised from the seed row's own notes
    action: str


def _promising(sub: IdeaSubmission, r: Reading) -> bool:
    return r.tier in ("bring_now", "ask_two")


def _built(sub: IdeaSubmission, r: Reading) -> bool:
    return r.stage in ("Prototype", "Pilot")


def _research(sub: IdeaSubmission, r: Reading) -> bool:
    return "research" in sub.exists


def _research_needs_funding(sub: IdeaSubmission, r: Reading) -> bool:
    return "research" in sub.exists and "funding" in sub.needs


def _sea_test(sub: IdeaSubmission, r: Reading) -> bool:
    text = f"{sub.title} {sub.solution} {sub.exists_detail}"
    return "test_access" in sub.needs and bool(OBSERVATION.search(text))


ROUTES: tuple[RouteRule, ...] = (
    RouteRule(
        "apelago-northern-blue-2027",
        "programme",
        ("blue",),
        _promising,
        "A'Pelago's 2027 accelerator for teams aiming to scale in the blue economy; equity-free.",
        "Show this read to A'Pelago so they can invite you to apply.",
    ),
    RouteRule(
        "helsinki-blue-economy-studio-2027",
        "programme",
        ("blue",),
        _built,
        "Early-stage teams of one or two founders, ideally with an MVP in market; open worldwide, with "
        "on-site bootcamps in Helsinki.",
        "Apply to the Studio before the deadline.",
    ),
    RouteRule(
        "apelago-lab2impact-2027",
        "programme",
        ("blue",),
        _research,
        "A'Pelago's programme for researchers becoming founders.",
        "Ask A'Pelago to tell you when Lab2Impact 2027 opens.",
    ),
    RouteRule(
        "emso-physical-access-2026",
        "proof_step",
        ("blue",),
        _sea_test,
        "Free access to a European sea observatory plus up to EUR 15,000 per proposal; universities and "
        "individual researchers may apply.",
        "Send a letter of intent to an observatory first; the facility must acknowledge it before the cut-off.",
    ),
    RouteRule(
        "bf-r2b",
        "funding",
        ("blue", "climate_circular"),
        _research_needs_funding,
        "Business Finland funds research organisations to take results towards a business; the team applies "
        "through its university.",
        "Ask your university's research services whether a Research to Business project fits.",
    ),
)
NO_ROUTE = (
    "No programme or funding route in our data fits this idea yet. A'Pelago can still read it if you bring it to them."
)


def instrument(instrument_id: str) -> dict:
    return next(i for i in seed.load("grants")["instruments"] if i["id"] == instrument_id)


def status_text(inst: dict, today: date) -> str:
    status, deadline = inst.get("status", "unknown"), parse_date(inst.get("deadline"))
    if deadline and deadline < today:
        return f"Closed {deadline:%d %b %Y}"
    if status in ("open", "continuous", "rolling", "open_no_date"):
        return f"Open, closes {deadline:%d %b %Y}" if deadline else "Open; no closing date published"
    if status in ("tba", "forthcoming", "coming", "unknown_2027"):
        return "Opens later; dates not announced"
    if status.startswith("closed"):
        return "Closed; next call not announced"
    if status == "open_unverified":
        return "Listed as open; dates not confirmed"
    return "Status not confirmed"


def check_title(label: str) -> str:
    """The title of the check step for a criterion, such as "Close the biggest gap: who pays"."""
    return f"Close the biggest gap: {label.lower()}"


def check_why(label: str, rung_label: str) -> str:
    """Why the check step comes first, such as "Public trace: none given. This answer changes ..."."""
    return f"{label}: {rung_label.lower()}. This answer changes the read more than anything else."


def steps(sub: IdeaSubmission, reading: Reading, *, today: date, public_record: bool = False) -> list[IdeaStep]:
    """At most three: the check that matters most (own submissions only), then the fitting routes,
    dated ones first."""
    found: list[IdeaStep] = []
    gaps = gap_order(reading.criteria)
    if gaps and not public_record:
        target = BY_ID[gaps[0].id]
        found.append(
            IdeaStep(
                rank=0,
                kind="check",
                title=check_title(target.label),
                action=target.self_check,
                why=check_why(target.label, gaps[0].rung_label),
            )
        )
    routes = []
    for rule in ROUTES:
        if sub.preset not in rule.presets or not rule.fits(sub, reading):
            continue
        inst = instrument(rule.instrument_id)
        deadline = parse_date(inst.get("deadline"))
        if deadline and deadline < today:
            continue
        routes.append(
            IdeaStep(
                rank=0,
                kind=rule.kind,
                title=inst["name"],
                action=rule.action,
                why=rule.why,
                status=status_text(inst, today),
                deadline=deadline,
                source_url=inst.get("url"),
                instrument_id=inst["id"],
            )
        )
    routes.sort(key=lambda s: (s.deadline or date.max, KIND_ORDER[s.kind]))
    chosen = (found + routes)[:MAX_STEPS]
    return [s.model_copy(update={"rank": i}) for i, s in enumerate(chosen, 1)]


def funding_note(found: list[IdeaStep]) -> str:
    """Honest about money before a company exists (from the Sprint grant's own published rules), and says
    so when no route fits at all."""
    sprint = instrument("bf-sprint")
    equity = sprint["other_hard_rules"][0].replace(">=", "at least")
    note = (
        f"No grant in our data funds a team before it has a company: {sprint['name']} needs a Finnish limited "
        f"company (Oy) with {equity}, so it is a step for later."
    )
    if any(s.kind == "funding" for s in found):
        note += " The research route above is the exception: it funds the university, not the team."
    return note if any(s.kind not in ("check", "invite") for s in found) else f"{NO_ROUTE} {note}"
