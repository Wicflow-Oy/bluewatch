"""Promise score (0-100) with the scout seed's weights; every part is shown. A ranking aid, not a prediction."""

from __future__ import annotations

import re
from datetime import date

from bluewatch import seed
from bluewatch.bridges.common import iso_dates, today_or_default
from bluewatch.models import HackathonProject, PlacementClass, PromiseScore

WEIGHTS = seed.load("hackathon_scout")["promise_score_weights"]
# The most each part can give, so every point is shown against its ceiling.
MAXIMA = {
    "placement": max(WEIGHTS["placement"].values()),
    "event_size": max(WEIGHTS["event_size"].values()),
    "partner_on_jury": WEIGHTS["partner_on_jury"],
    "theme_fit": WEIGHTS["theme_fit_max"],
    "recency": max(WEIGHTS["recency"].values()),
    "prototype": max(WEIGHTS["prototype"].values()),
    "pre_company": max(WEIGHTS["pre_company"].values()),
    "organiser_offers_support": WEIGHTS["organiser_offers_support"],
}
PARTNERS = ("Redstone", "A'Pelago")

BLUE_CORE = re.compile(
    r"\b(ports?|harbou?rs?|ships?|shipping|vessels?|boats?|maritime|marine|oceans?|seas?|offshore|aquaculture|"
    r"fish\w*|seaweed|algae|coast\w*|subsea|underwater|naval|baltic|dredg\w*|hulls?)\b",
    re.I,
)
VERTICAL_TERMS = {
    "maritime_ports": r"ports?|harbou?rs?|ships?|shipping|vessels?|boats?|workboats?|ferr(?:y|ies)|maritime|"
    r"dredg\w*|fairways?|berths?|hulls?|surface drones?|usvs?",
    "marine_intelligence": r"data|forecast\w*|monitor\w*|sensors?|sensing|situational awareness|satellites?|"
    r"mapping|analytics|detect\w*|tracking|digital twins?|predict\w*",
    "ocean_infra_clean_energy": r"offshore wind|wind turbines?|floating wind|wave energy|tidal|hydrogen|"
    r"shore power|charging|batter(?:y|ies)|energy|cables?|renewables?",
    "blue_biotech_water": r"aquaculture|fish farm\w*|seaweed|algae|algal|kelp|mussels?|shellfish|water quality|"
    r"wastewater|drinking water|desalination|biotech\w*|nutrients?|microplastics?|plastics?",
}
VERTICALS = {name: re.compile(rf"\b(?:{terms})\b", re.I) for name, terms in VERTICAL_TERMS.items()}
BUYER_PULL = re.compile(r"challenge (?:from|by|set by|posed by)\b|answered the [^.;()]{0,60}challenge", re.I)
DUAL_USE = re.compile(r"\b(naval|defen[cs]e|military|warfare|low-observable|weapons?|combat)\b", re.I)
# Theme fit (max 20): blue core 8, a named challenge owner 4, 3 per preset vertical (two at most),
# a Finnish project 2 (the partners' home market), and 3 off for a defence-leaning idea.
THEME_POINTS = {"blue_core": 8, "buyer_pull": 4, "per_vertical": 3, "max_verticals": 2, "home": 2, "dual_use": -3}

BUILT = re.compile(
    r"\b(prototypes?|prototyped|piloted|pilot (?:project|test|study)|\d+-day pilot|tested|field[- ]tests?|"
    r"trials?|deployed|demo facility|working (?:system|model|prototype)|mvp)\b",
    re.I,
)
TEAM_COUNT = re.compile(r"(\d[\d,]*)\+?\s+(?:finalist\s+)?(?:teams|finalists)\b", re.I)
JURY = re.compile(r"jury[^.;]*?\b(redstone|a'?pelago)\b", re.I)
SUPPORT = re.compile(
    r"supports? teams|from idea development to investment|incubat\w*|post-event support|in-kind support", re.I
)
NEGATED = re.compile(r"\b(?:not|no)\b[^;,()]*")
_MONTHS = {m: i for i, m in enumerate(("jan feb mar apr may jun jul aug sep oct nov dec").split(), start=1)}


def _texts(project: HackathonProject) -> str:
    """Everything the row and its verified plan say about the event and the result."""
    verified = project.meta.get("verified") or {}
    fields = (
        project.placement,
        project.organiser,
        project.edition,
        project.meta.get("theme"),
        verified.get("placement"),
        verified.get("organiser_note"),
    )
    return " ".join(f for f in fields if f)


def idea_text(project: HackathonProject) -> str:
    return f"{project.team_or_project} {project.idea or ''}"


def placement_class(project: HackathonProject) -> PlacementClass:
    # A negated clause ("not the local winner", "no award") says what the team did not get, so it never counts.
    text = NEGATED.sub("", (project.placement or "").lower())
    if project.meta.get("kind") == "listed":
        return "listed"
    if "runner-up" in text:
        return "3rd" if re.search(r"\b(2nd|second) runner-up", text) else "2nd"
    if re.search(r"\b(1st|first)\b|\bwinner\b|\bchampion\b|top honours", text):
        return "1st"
    if re.search(r"\b(2nd|second)\b", text):
        return "2nd"
    if re.search(r"\b(3rd|third)\b", text):
        return "3rd"
    if re.search(r"(?<!semi-)finalist|award|prize|honourable mention|merit", text):
        return "finalist_or_award"
    return "listed"


def team_count(project: HackathonProject) -> int | None:
    counts = [int(n.replace(",", "")) for n in TEAM_COUNT.findall(_texts(project))]
    return max(counts) if counts else None


def event_date(project: HackathonProject, today: date) -> date | None:
    """The latest stated date that has passed; else the stated month (its first day); else unknown."""
    passed = [d for d in iso_dates(project.date) if d <= today]
    if passed:
        return max(passed)
    text = project.date or ""
    month = re.search(r"\b(\d{4})-(\d{2})\b", text)
    if month:
        return date(int(month.group(1)), int(month.group(2)), 1)
    named = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{4})\b", text, re.I)
    return date(int(named.group(2)), _MONTHS[named.group(1).lower()], 1) if named else None


def juror(project: HackathonProject) -> str | None:
    """A partner that sat on the event's jury, which makes a warm route."""
    match = JURY.search(_texts(project))
    return next((p for p in PARTNERS if match and p.lower().replace("'", "") in match.group(1).lower()), None)


def is_dual_use(project: HackathonProject) -> bool:
    return bool(DUAL_USE.search(idea_text(project)))


def is_concept(project: HackathonProject) -> bool:
    return not BUILT.search(f"{idea_text(project)} {project.meta.get('later_company') or ''}")


def theme_fit(project: HackathonProject) -> int:
    text = idea_text(project)
    points = THEME_POINTS["blue_core"] if BLUE_CORE.search(text) else 0
    points += THEME_POINTS["buyer_pull"] if BUYER_PULL.search(text) else 0
    verticals = sum(1 for pattern in VERTICALS.values() if pattern.search(text))
    points += THEME_POINTS["per_vertical"] * min(verticals, THEME_POINTS["max_verticals"])
    points += THEME_POINTS["home"] if (project.country or "").startswith("Finland") else 0
    points += THEME_POINTS["dual_use"] if is_dual_use(project) else 0
    return max(0, min(points, WEIGHTS["theme_fit_max"]))


def _size(count: int | None) -> int:
    sizes = WEIGHTS["event_size"]
    if count is not None and count >= 15:
        return sizes[">=15 teams"]
    if count is not None and count >= 8:
        return sizes[">=8 teams"]
    return sizes["smaller or unknown"]


def _recency(when: date | None, today: date) -> int:
    if when is None:
        return 0  # unknown date: no points, and the plan lists it as a gap
    days = (today - when).days
    recency = WEIGHTS["recency"]
    if days <= 92:
        return recency["<=3 months"]
    if days <= 183:
        return recency["3-6 months"]
    return recency["6-12 months"] if days <= 365 else 0


def promise_score(project: HackathonProject, *, today: date | None = None) -> PromiseScore:
    today = today_or_default(today)
    parts = {
        "placement": WEIGHTS["placement"][placement_class(project)],
        "event_size": _size(team_count(project)),
        "partner_on_jury": WEIGHTS["partner_on_jury"] if juror(project) else 0,
        "theme_fit": theme_fit(project),
        "recency": _recency(event_date(project, today), today),
        "prototype": WEIGHTS["prototype"]["concept only or unclear" if is_concept(project) else "built or tested"],
        "pre_company": WEIGHTS["pre_company"][
            "no company found" if project.company_status == "none_found" else "already a company"
        ],
        "organiser_offers_support": WEIGHTS["organiser_offers_support"] if SUPPORT.search(_texts(project)) else 0,
    }
    return PromiseScore(
        total=float(sum(parts.values())),
        parts={k: float(v) for k, v in parts.items()},
        maxima={k: float(v) for k, v in MAXIMA.items()},
    )
