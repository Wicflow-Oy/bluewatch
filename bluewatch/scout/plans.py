"""Contact plans for promising pre-company teams: gaps as questions, one offer, an organisation-level route.

Plans only. Sending belongs to the outreach desk, after human approval.
"""

from __future__ import annotations

import re
from datetime import date

from bluewatch import seed
from bluewatch.bridges.common import today_or_default
from bluewatch.models import (
    ContactPlan,
    ContactPlanDraft,
    Evidence,
    HackathonProject,
    Mode,
    NextCheck,
    Route,
    ScoutProject,
)
from bluewatch.scout.projects import load_projects
from bluewatch.scout.score import event_date, is_concept, is_dual_use, juror, placement_class, promise_score

PERSONAL = re.compile(r"@|mailto:|linkedin\.com/in/|github\.com|facebook\.com|instagram\.com|(?:x|twitter)\.com/", re.I)
INSTITUTION = re.compile(
    r"(?:[A-Z][\w.'’-]*\s+){0,4}(?:University|College|Polytechnic)(?:\s+of(?:\s+[A-Z][\w.'’-]*){1,3})?"
    r"|University of(?:\s+[A-Z][\w.'’-]*){1,3}"
)
CHALLENGE_OWNER = re.compile(
    r"challenge (?:from|by|set by|posed by) ((?:the )?[^,;()]+)|answered the ([^.;()]+?) challenge", re.I
)
ORGANISER_CODE = re.compile(r"^\[[A-Z]{3}\d{2}[A-Z]?\]\s*")
LABELS = {"1st": "winner", "2nd": "runner-up", "3rd": "third place", "finalist_or_award": "finalist", "listed": "team"}
COUNT_WORDS = {1: "one", 2: "two", 3: "three"}
PROGRAMME_ID = "apelago-northern-blue-2027"
REDSTONE_OFFER = ("A first call with Redstone about building a company from the project", "a first call with Redstone")
DEMO_FLAG = "Plan only: the outreach desk sends after human approval; sending is off in this workspace"


def public_url(url: str | None) -> str | None:
    """The first organisation page in a source field; a note in place of a link ("not recorded (...)") and
    personal or code-host pages are never used."""
    first = re.split(r"\s+[;|]\s+", url)[0] if url else None
    return first if first and first.startswith(("https://", "http://")) and not PERSONAL.search(first) else None


def _clean(text: str | None) -> str | None:
    return re.sub(r"\s*\(.*$", "", text).strip() if text else None


def project_name(project: HackathonProject) -> str:
    """The team or project as a message can name it: without the organiser's code ("[CAD05] ") or a trailing
    aside ("(no short project name published)", "(KAUST, Saudi Arabia)")."""
    return _clean(ORGANISER_CODE.sub("", project.team_or_project)) or project.team_or_project


def _unnamed(name: str) -> bool:
    """True when the organiser published no project name, only a description of the team ("Unnamed winning
    team", "University College Dublin master's student team")."""
    return bool(re.search(r"^unnamed\b|\bteam$", name, re.I))


def team_phrase(project: HackathonProject) -> str:
    """How a message names the team: "the KU.exe team", and "the winning team" for "Unnamed winning team"."""
    base = re.sub(r"^(?:the|unnamed)\s+", "", project_name(project), flags=re.I)
    return f"the {base}" if base.lower().endswith("team") else f"the {base} team"


def _city(text: str | None) -> str | None:
    """A city without the research aside; "Not stated" and "Online" are no city at all."""
    place = _clean(text)
    return None if not place or place.lower().startswith(("not stated", "online")) else place


def _online(project: HackathonProject) -> bool:
    return any((text or "").lower().startswith("online") for text in (project.city, project.country))


def place(project: HackathonProject) -> str | None:
    """Where the result was won, for prose: "Split, Croatia" or "Online", without research asides; None when
    the organiser does not say. A country the research only inferred is left out."""
    if _online(project):
        return "Online"
    country = None if "inferred" in (project.country or "").lower() else _city(project.country)
    return ", ".join(dict.fromkeys(p for p in (_city(project.city), country) if p)) or None


def short_event(project: HackathonProject) -> str:
    return _clean(project.event) or project.event


def _organiser(project: HackathonProject) -> str | None:
    text = (project.meta["verified"].get("organiser") or project.organiser or "").strip()
    if not text or text.lower().startswith("not "):
        return None
    first = re.split(r";|, | \+ | with | \(", text)[0]
    return re.sub(r"^local:\s*", "", first).strip()  # the network's local host, named without the label


def _institution(project: HackathonProject) -> str | None:
    verified = project.meta["verified"].get("institution")
    if verified and not verified.lower().startswith("not "):
        return verified
    match = INSTITUTION.search(f"{project.team_or_project} {project.idea or ''}")
    return match.group(0).strip() if match else None


def _challenge_owner(project: HackathonProject) -> str | None:
    match = CHALLENGE_OWNER.search(project.idea or "")
    return (match.group(1) or match.group(2)).strip() if match else None


def route_ladder(project: HackathonProject) -> list[Route]:
    """Organiser or warm route first, then the university office, the team's public channel, the next
    event, and always the opt-in link. Organisations only: no person's name or contact details."""
    verified, event = project.meta["verified"], short_event(project)
    rungs: list[tuple[str, str, str, str | None]] = []
    partner = juror(project)
    if partner:
        rungs.append(
            (
                "warm_intro",
                f"{partner} (a juror at {event})",
                f"A person at {partner} follows up through the relationship from the event",
                None,
            )
        )
    organiser = _organiser(project)
    if organiser:
        how = verified.get("organiser_how") or "Ask the organiser to forward the invitation to the team"
        page = verified.get("organiser_page") or project.source_url
        rungs.append(("organiser", organiser, how, public_url(page)))
    institution = _institution(project)
    if institution:
        rungs.append(
            (
                "university_office",
                f"{institution} (innovation or technology-transfer office)",
                "Look up the office's public contact page (not yet checked)",
                None,
            )
        )
    rungs.append(
        (
            "team_public_channel",
            "The team's own public project channel",
            "None found in the sources read; use only a project site or contact form the team publishes",
            None,
        )
    )
    series = re.sub(r"\s*\b(?:19|20)\d{2}\b.*$", "", event).strip() or event
    rungs.append(("event", f"The next {series} event", "Meet the team in person (next edition not announced)", None))
    rungs.append(
        (
            "opt_in",
            "Student idea programme (opt-in link)",
            "Every forwarded message carries the opt-in link; the team chooses whether to reply",
            None,
        )
    )
    return [Route(rank=i, kind=k, organisation=o, how=h, contact_page_url=u) for i, (k, o, h, u) in enumerate(rungs, 1)]


def _gap(project: HackathonProject, field: str, claim: str, question: str | None, how: str | None = None) -> Evidence:
    check = NextCheck(kind="ask_founder", question=question) if question else NextCheck(kind="public_check", how=how)
    return Evidence(
        id=f"{project.id}:gap:{field}",
        project_id=project.id,
        field=field,
        claim=claim,
        state="unknown",
        why_unknown="Not stated on the organiser's results page",
        next_check=check,
        url=public_url(project.source_url),
        source_family="hackathon_results",
        tag="read",
    )


def gaps(project: HackathonProject, *, today: date) -> list[Evidence]:
    """What the results page does not say, in the order worth asking."""
    # A missing or hedged solution name ("X (unconfirmed ...)") is no name to put to the team.
    named = project.meta["verified"].get("solution_name")
    solution = named if named and "(" not in named else project_name(project)
    if _unnamed(solution):
        solution = "the project"
    found = [
        _gap(
            project,
            "continuing",
            "Whether the team continues the project",
            f"Are you continuing {solution} after {short_event(project)}?",
        )
    ]
    if is_concept(project):
        question = (
            "What exists beyond the concept: a simulation, a model or a prototype?"
            if "concept" in (project.idea or "").lower()
            else "What exists today: a model, a prototype or a field test?"
        )
        found.append(_gap(project, "built", "What has been built or tested", question))
    owner = _challenge_owner(project)
    if is_dual_use(project):
        found.append(_gap(project, "market", "Who the buyers are", "Defence buyers, civil uses, or both?"))
    elif owner:
        found.append(
            _gap(
                project,
                "pilot_interest",
                "Whether a buyer wants a pilot",
                f"Has {owner}, or another buyer, shown interest in a pilot?",
            )
        )
    owner_of_results = (
        "Who owns the results: the team or the university?"
        if _institution(project)
        else "Who owns the concept: the team or a university?"
    )
    found.append(_gap(project, "ownership", "Who owns the results", owner_of_results))
    if project.company_status == "check":
        found.append(
            _gap(
                project, "company", "Whether a company exists", "Is there a registered company behind the project yet?"
            )
        )
    if event_date(project, today) is None:
        found.append(
            _gap(
                project,
                "event_date",
                "When the result was announced",
                None,
                how="Re-read the organiser's results page for the date",
            )
        )
    return found


def _offer(project: HackathonProject, mode: Mode) -> tuple[str, str]:
    """One offer, with its short form for the subject line: the workspace offers its own next step, so only
    A'Pelago's workspace offers A'Pelago's programme."""
    partner = juror(project)
    if partner:
        offer = f"A follow-up conversation with {partner}, whose juror already saw the pitch"
        return offer, f"a follow-up from {partner}"
    if mode == "redstone":
        return REDSTONE_OFFER
    programme = next(g for g in seed.load("grants")["instruments"] if g["id"] == PROGRAMME_ID)
    name = programme["name"].split(" (")[0]
    status = "applications open" if programme["status"] == "open" else "dates to be announced"
    return f"{name} ({status}), for teams aiming to scale in the blue economy", "an A'Pelago programme"


def public_project(project: HackathonProject, *, today: date) -> ScoutProject:
    """The project as the organiser published it, for the browser: structured facts, no research asides."""
    when = event_date(project, today)
    return ScoutProject(
        id=project.id,
        team_or_project=project_name(project),
        event=project.event,
        year=when.year if when else None,
        city=_city(project.city),
        country_code=project.meta.get("country_code"),
        online=_online(project),
        placement=placement_class(project),
        idea=project.idea,
        source_url=public_url(project.source_url),
        company_status=project.company_status,
    )


def contact_plan(project: HackathonProject, *, today: date | None = None, mode: Mode = "apelago") -> ContactPlan:
    today = today_or_default(today)
    found = gaps(project, today=today)
    questions = [g.next_check.question for g in found if g.next_check.question]
    offer, offer_short = _offer(project, mode)
    routes = route_ladder(project)
    target = next((r for r in routes if r.kind in ("organiser", "university_office")), None)
    label, event, team = LABELS[placement_class(project)], short_event(project), project_name(project)
    asked = questions[:3]
    draft = None
    if target:
        count = COUNT_WORDS[len(asked)]
        draft = ContactPlanDraft(
            to_route_rank=target.rank,
            subject=f"{event} {label} {team}: {offer_short} and {count} questions",
            points=[
                f"Who we are and why: {team} ({label}) at {event}",
                f"The offer: {offer}",
                f"{count.capitalize()} questions from the gaps: " + " ".join(asked),
                "An opt-in link, plus a request to forward it to the team",
                "Footer: marketing notice, our details, how to object",
            ],
        )
    flags = [DEMO_FLAG]
    if juror(project):
        flags.append(f"Warm route: {juror(project)} sat on the jury")
    if is_dual_use(project):
        flags.append("Dual use: defence-leaning concept; check fund policy before any investment talk")
    if project.company_status == "check":
        flags.append("Company status unclear: check the registers before any contact")
    return ContactPlan(
        project_id=project.id,
        promise_score=promise_score(project, today=today),
        gaps=found,
        questions=questions,
        offer=offer,
        route_ladder=routes,
        draft=draft,
        flags=flags,
        project=public_project(project, today=today),
    )


def plans(top_n: int = 20, *, today: date | None = None, mode: Mode = "apelago") -> list[ContactPlan]:
    """Plans for the most promising pre-company teams, highest promise score first, offering the workspace's
    own next step."""
    today = today_or_default(today)
    candidates = [p for p in load_projects() if p.company_status != "already_a_company" and p.in_window]
    candidates.sort(key=lambda p: (-promise_score(p, today=today).total, p.id))
    return [contact_plan(p, today=today, mode=mode) for p in candidates[:top_n]]
