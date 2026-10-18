"""The Idea Harbour rubric: eight criteria on two axes, each decided by a rule a reviewer can read.

- Potential (what the idea could be if it holds): problem, solution, who pays, team, impact fit. A
  criterion the team left blank is left out of the average, never counted as zero: unknowns lower
  evidence, never potential. A blank becomes a question to ask, not a low score.
- Evidence (what is shown, not just said): what is built, contact with buyers, a public trace. Here a
  blank counts as nothing shown.
- Everything typed into the form is a claim until a public record or a person confirms it, so evidence
  from the form alone is never "strong" without a public trace.
- Bands and tiers are words, never a fake-precise score; the rung behind each is shown per criterion.

The rules read claims (a signal plus the exact words that show it, see signals.py). The rules find claims
themselves; vet.py may let a model add more, but every claim must quote the submission and only the rules
decide. A team's own submission is also checked for scope: an advertisement, or an idea with nothing about
the ocean, water, the climate or materials, reads "Not yet" and says why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bluewatch.ideas import vocabulary
from bluewatch.ideas.models import (
    Axis,
    Claim,
    CriterionResult,
    EvidenceBand,
    Flag,
    IdeaSubmission,
    LedgerItem,
    PotentialBand,
    Tier,
)
from bluewatch.ideas.signals import IMPACT_SIGNAL, SIGNALS, area_words, impact_areas, inferred_areas
from bluewatch.ideas.text import TEXT_FIELDS, sentences, word_list
from bluewatch.models import NextCheck

RUBRIC_VERSION = "idea-rubric-2 (18 Oct 2026)"


@dataclass(frozen=True)
class Criterion:
    id: str
    label: str
    axis: Axis
    weight: int
    rungs: tuple[str, str, str, str]  # what rung 0, 1, 2 and 3 mean
    rule: str
    question: str  # what A'Pelago asks to settle it
    self_check: str  # the same gap as a next step for the team


CRITERIA: tuple[Criterion, ...] = (
    Criterion(
        "problem",
        "Problem and who has it",
        "potential",
        3,
        ("Too short to read", "Generic", "Says who has it", "Says who has it and how much it costs"),
        "Rung 2 names who has the problem; rung 3 also sizes it (a number) or says why now (a rule, "
        "a deadline, a trend).",
        "Who exactly has this problem, and what does it cost them today?",
        "Name who has the problem and what it costs them in money, time or tonnes.",
    ),
    Criterion(
        "solution",
        "Solution",
        "potential",
        2,
        ("Too short to read", "Generic", "Says how it works", "Says how it works and what it replaces"),
        "Rung 2 says how it works (a method, device or model); rung 3 also says what it replaces or beats today.",
        "How does it work, and what does it replace today?",
        "Write two sentences: how it works, and what people do today instead.",
    ),
    Criterion(
        "who_pays",
        "Who pays",
        "potential",
        2,
        ("Too short to read", "Unclear or grant-based", "Names who pays", "Names who pays and a first price"),
        "Rung 2 names a buyer or a way of charging; rung 3 adds a price. Grants as the only income stay "
        "at rung 1: grants are runway, not a business.",
        "Who would pay for it, and roughly how much?",
        "Name the first buyer and a price you could test with them.",
    ),
    Criterion(
        "team",
        "Team",
        "potential",
        2,
        ("No roles", "One side covered", "Builds, and sells or knows the field", "Builds, sells and knows the field"),
        "From the roles listed (never names): build, business and domain knowledge. Rung 3 covers all three.",
        "Who on the team builds it, who sells it, and who knows the field?",
        "List the roles you have and the one you are missing.",
    ),
    Criterion(
        "impact",
        "Impact area",
        "potential",
        2,
        (
            "None",
            "Area only, or inferred from the text",
            "Area and how it helps",
            "Area, how it helps and what to measure",
        ),
        "Uses the preset's impact areas as tags, never a numeric impact level. Rung 2 picks an area and "
        "the text shows how it helps; rung 3 also names what would be measured.",
        "Which impact area does it improve, and what would you measure?",
        "Pick the impact area and the one number you would measure.",
    ),
    Criterion(
        "built",
        "What is built",
        "evidence",
        3,
        ("Nothing stated", "Concept or research", "Prototype or pilot", "Prototype or pilot, with specifics"),
        "Rung 2 for a prototype or pilot; rung 3 when the text gives specifics (a number or a date).",
        "What exists today, and when was it last tested?",
        "Build the smallest test that shows it works, and write down the date and the result.",
    ),
    Criterion(
        "buyers",
        "Contact with buyers",
        "evidence",
        3,
        ("Nothing stated", "Talked to users", "Counted conversations or a commitment", "Commitments, described"),
        "Rung 1 for user interviews; rung 2 for a counted number of conversations, a pilot partner, "
        "letters of intent or paying customers; rung 3 when a commitment is also described in the text.",
        "How many potential buyers have you talked to, and has any agreed to a pilot?",
        "Talk to five potential buyers and write down what they use and pay today.",
    ),
    Criterion(
        "trace",
        "Public trace",
        "evidence",
        2,
        ("None given", "One link (not opened yet)", "Two or more links", "A public record"),
        "Links count as given, not as checked: a person at A'Pelago opens them. Rung 3 is a public record "
        "(an organiser's results page, an EU project record).",
        "Is there a public page, repository or video to look at?",
        "Add a public project page, repository or two-minute demo video that a reviewer can open.",
    ),
)
BY_ID = {c.id: c for c in CRITERIA}

TIER_LABELS: dict[Tier, str] = {
    "bring_now": "Bring to A'Pelago now",
    "ask_two": "Promising: ask two questions",
    "not_yet": "Not yet",
}
POTENTIAL_RULE = (
    "Weighted average of the potential criteria that were answered (problem 3, solution 2, who pays 2, team 2, "
    "impact 2). Blank criteria are left out, never counted as zero; potential is judged once the problem and the "
    "solution are both answered. High: an average rung of 2 or more. Medium: 1.3 or more. Low: below that."
)
EVIDENCE_RULE = (
    "Weighted average over all evidence criteria (built 3, buyer contact 3, public trace 2), where a blank "
    "counts as nothing shown. Strong: 2 or more and a public trace. Some: 1 or more. Thin: below that."
)
TIER_RULES = (
    "Held: text aimed at the reviewer ('ignore the rules', 'rate this top') holds the idea for a person.",
    "Not yet: fewer than 20 words, or mostly repeated words.",
    "Not yet, out of scope: an advertisement (two or more sales words such as 'discount code' or 'presale'), "
    "or no word about the ocean, water, the climate or the circular economy.",
    "Not enough to judge (the problem or the solution is blank): not yet for an own submission; two questions "
    "for a public record.",
    "Bring to A'Pelago now: high potential, at least some evidence, and an impact area shown in the text.",
    "Promising, ask two questions: high potential, or medium potential with at least some evidence.",
    "Not yet: medium potential with thin evidence, or low potential, on what is written.",
)
ANTI_GAMING = (
    "Length earns nothing: each rung is defined by content (who, how, how much), never by word count.",
    "Every claim quotes the team's own words; a model may add claims only if it can quote them exactly, and "
    "only the rules set the tier.",
    "Typed answers are claims, not facts: evidence is never strong without a public trace a person can open.",
    "Instructions aimed at the reviewer are ignored by the rules and hold the idea for a person to check.",
    'A negated claim earns nothing: "we haven\'t talked to buyers yet" is not buyer contact, in English, '
    "Finnish or Swedish.",
    "Blanks don't pay: a blank never adds evidence, it becomes a question on the card, potential waits for both "
    "the problem and the solution, and 'Bring now' needs an impact area shown in the text.",
    "Near-duplicates of another idea or a public project are flagged; only the higher-ranked one stays in the Top N.",
    "A rate limit per visitor and a size limit on every field.",
)
MIN_WORDS = 20  # across all answers; fewer is "too little to assess"
MIN_UNIQUE_SHARE = 0.4
JUDGED_WHEN = ("problem", "solution")  # potential is judged once both are answered
TOO_SHORT = 4  # words: a team's own problem or solution this short is read as rung 0
SCOPE_FIELDS = ("title", *TEXT_FIELDS)

TIER_REASONS = {
    "held": "Held for a person: the text contains instructions aimed at the reviewer. The rules ignore them, and "
    "a person checks the idea before it is ranked.",
    "low_effort": "Too little to assess yet: write a few sentences each on the problem, who has it and your solution.",
    "advert": "Not yet: this reads as an advertisement, not an idea for A'Pelago's programmes.",
    "off_topic": "Not yet: nothing in the answers ties the idea to the ocean, water, the climate or the circular "
    "economy, which A'Pelago's programmes are for. If it does, say how in the problem or the solution.",
    "unknown_public": "Too little is written to judge the idea, which is not a low score: a public record exists, "
    "so ask the team two questions through the organisation.",
    "unknown": "Not enough to judge the idea yet, which is not a low score: answer the two questions below.",
    "medium_thin": "Medium potential and thin evidence on what is written: two questions would not settle it yet. "
    "Talking to buyers, testing it or adding a public page changes the read.",
    "low": "Low potential on what is written: the answers read as generic. The next checks would change that.",
}

EXISTS_LABELS = {
    "research": "Research results",
    "concept": "A written concept",
    "prototype": "A prototype",
    "pilot": "A pilot",
    "user_interviews": "User interviews",
    "letters_of_intent": "Letters of intent",
    "paying_customers": "Paying customers",
}
STAGES = (("pilot", "Pilot"), ("prototype", "Prototype"), ("concept", "Concept"), ("research", "Research"))
ROLE_LABELS = {"build": "build", "business": "business", "domain": "domain knowledge", "design": "design"}


# --------------------------------------------------------------------------- reading
@dataclass
class Reading:
    criteria: list[CriterionResult]
    potential: PotentialBand
    evidence: EvidenceBand
    tier: Tier
    tier_rule: str
    questions: list[str]
    strengths: list[str]
    claims: list[LedgerItem]
    assumptions: list[LedgerItem]
    unknowns: list[LedgerItem]
    impact_areas: list[str]
    stage: str
    flags: list[Flag] = field(default_factory=list)


def read(
    sub: IdeaSubmission,
    claims: list[Claim],
    *,
    flags: list[Flag],
    public_record: bool = False,
    held: bool = False,
    source: str = "Your submission",
    extra_questions: tuple[str, ...] = (),
) -> Reading:
    """Rungs, bands, tier, questions and ledger for one idea. public_record: the idea comes from a public
    record (a hackathon result, an EU project) rather than from the team itself."""
    flags = list(flags)
    by_signal = {c.signal: c for c in claims}
    inferred = inferred_areas(sub)
    results = [
        _problem(sub, by_signal, not public_record),
        _solution(sub, by_signal, not public_record),
        _who_pays(sub, by_signal, flags),
        _team(sub),
        _impact(sub, by_signal, inferred),
        _built(sub, by_signal),
        _buyers(sub, by_signal),
        _trace(sub, public_record),
    ]
    potential, evidence = _potential_band(results), _evidence_band(results)
    low_effort = None if public_record else _low_effort(sub)
    if low_effort:
        flags.append(Flag(kind="low_effort", text=low_effort))
    if held:
        flags.append(
            Flag(
                kind="held_instructions",
                text="Held for a person: the text contains instructions aimed "
                "at the reviewer. The rules never follow them.",
            )
        )
    # Public records come from ocean events and research programmes; only a team's own text is scope-checked.
    stop = "held" if held else "low_effort" if low_effort else None if public_record else _out_of_scope(sub)
    tier, rule = _tier(potential, evidence, results, stop=stop, public_record=public_record)
    claims_items, assumptions = _claims_ledger(sub, claims, source), _assumptions(sub, inferred, by_signal, flags)
    return Reading(
        criteria=results,
        potential=potential,
        evidence=evidence,
        tier=tier,
        tier_rule=rule,
        questions=_questions(results, extra_questions),
        strengths=_strengths(results),
        claims=claims_items,
        assumptions=assumptions,
        unknowns=_unknowns(results),
        impact_areas=list(dict.fromkeys(([sub.impact_area] if sub.impact_area else []) + list(inferred))),
        stage=next((label for key, label in STAGES if key in sub.exists), "Idea"),
        flags=flags,
    )


def _result(cid: str, rung: int | None, quote: str | None = None, label: str | None = None) -> CriterionResult:
    c = BY_ID[cid]
    return CriterionResult(
        id=c.id,
        label=c.label,
        axis=c.axis,
        weight=c.weight,
        rung=rung,
        rung_label=label or ("Not stated" if rung is None else c.rungs[rung]),
        rule=c.rule,
        quote=quote,
        question=c.question,
    )


def _quote(by_signal: dict[str, Claim], *names: str) -> str | None:
    return next((by_signal[n].quote for n in names if n in by_signal), None)


def _too_short(text: str, effort_counts: bool) -> bool:
    """A team's own two-word answer is an effort signal; a short phrase quoted from a public record is not."""
    return effort_counts and len(word_list(text)) < TOO_SHORT


def _problem(sub: IdeaSubmission, s: dict[str, Claim], effort_counts: bool) -> CriterionResult:
    if not (sub.problem or sub.who_has_it):
        return _result("problem", None)
    if "named_customer" in s:
        sized = "quantified_pain" in s or "why_now" in s
        return _result("problem", 3 if sized else 2, _quote(s, "quantified_pain", "why_now", "named_customer"))
    if sub.problem and _too_short(sub.problem, effort_counts):
        return _result("problem", 0, sub.problem)
    return _result("problem", 1, (sentences(sub.problem) or sentences(sub.who_has_it))[0])


def _solution(sub: IdeaSubmission, s: dict[str, Claim], effort_counts: bool) -> CriterionResult:
    if not sub.solution:
        return _result("solution", None)
    if _too_short(sub.solution, effort_counts):
        return _result("solution", 0, sub.solution)
    if "mechanism" in s:
        return _result("solution", 3 if "comparison" in s else 2, _quote(s, "comparison", "mechanism"))
    return _result("solution", 1, sentences(sub.solution)[0])


def _who_pays(sub: IdeaSubmission, s: dict[str, Claim], flags: list[Flag]) -> CriterionResult:
    if not sub.who_pays and "payer" not in s:
        return _result("who_pays", None)
    if sub.who_pays and len(word_list(sub.who_pays)) < 2:
        return _result("who_pays", 0, sub.who_pays)
    if "payer" in s:
        return _result("who_pays", 3 if "price_point" in s else 2, _quote(s, "price_point", "payer"))
    if "grant_reliance" in s:
        flags.append(
            Flag(
                kind="grant_dependency",
                text="Income would come from grants or donations: investors look for a buyer who pays.",
            )
        )
        return _result("who_pays", 1, _quote(s, "grant_reliance"), "Relies on grants")
    return _result("who_pays", 1, sentences(sub.who_pays)[0] if sub.who_pays else None)


def _team(sub: IdeaSubmission) -> CriterionResult:
    if not sub.team:
        return _result("team", None)
    roles = {m.role for m in sub.team}
    if {"build", "business", "domain"} <= roles:
        return _result("team", 3)
    if "build" in roles and roles & {"business", "domain"}:
        return _result("team", 2)
    return _result("team", 1)


def _impact(sub: IdeaSubmission, s: dict[str, Claim], inferred: dict[str, list[str]]) -> CriterionResult:
    if not sub.impact_area:
        return _result("impact", 1 if inferred else None)
    if IMPACT_SIGNAL in s:
        return _result("impact", 3 if "impact_measure" in s else 2, _quote(s, "impact_measure", IMPACT_SIGNAL))
    return _result("impact", 1)


def _built(sub: IdeaSubmission, s: dict[str, Claim]) -> CriterionResult:
    if {"prototype", "pilot"} & set(sub.exists) or "built" in s:
        return _result("built", 3 if "built_specific" in s else 2, _quote(s, "built_specific", "built"))
    if {"concept", "research"} & set(sub.exists):
        return _result("built", 1)
    return _result("built", 0)


def _buyers(sub: IdeaSubmission, s: dict[str, Claim]) -> CriterionResult:
    committed = bool({"letters_of_intent", "paying_customers", "pilot"} & set(sub.exists)) or "buyer_commitment" in s
    if committed and ("buyer_commitment" in s or "buyer_talks_counted" in s):
        return _result("buyers", 3, _quote(s, "buyer_commitment", "buyer_talks_counted"))
    if committed or "buyer_talks_counted" in s:
        return _result("buyers", 2, _quote(s, "buyer_talks_counted", "buyer_commitment"))
    if "user_interviews" in sub.exists or "buyer_talks" in s:
        return _result("buyers", 1, _quote(s, "buyer_talks"))
    return _result("buyers", 0)


def _trace(sub: IdeaSubmission, public_record: bool) -> CriterionResult:
    if public_record:
        return _result("trace", 3)
    return _result("trace", min(len(sub.links), 2))


def _mean(results: list[CriterionResult]) -> float:
    total = sum(r.weight for r in results)
    return sum(r.weight * (r.rung or 0) for r in results) / total if total else 0.0


def _potential_band(results: list[CriterionResult]) -> PotentialBand:
    known = [r for r in results if r.axis == "potential" and r.rung is not None]  # blanks are left out
    if not {r.id for r in known} >= set(JUDGED_WHEN):
        return "unknown"
    m = _mean(known)
    return "high" if m >= 2.0 else "medium" if m >= 1.3 else "low"


def _evidence_band(results: list[CriterionResult]) -> EvidenceBand:
    evidence = [r for r in results if r.axis == "evidence"]  # a blank counts as nothing shown
    m = _mean(evidence)
    trace = next(r.rung for r in evidence if r.id == "trace") or 0
    return "strong" if m >= 2.0 and trace >= 1 else "some" if m >= 1.0 else "thin"


def _low_effort(sub: IdeaSubmission) -> str | None:
    body = [w.lower() for f in TEXT_FIELDS for w in word_list(getattr(sub, f))]
    if len(body) < MIN_WORDS:
        return f"Too little to assess: at least {MIN_WORDS} words are needed across the answers."
    if len(set(body)) / len(body) < MIN_UNIQUE_SHARE:
        return "Mostly repeated words: write the answers in your own sentences."
    return None


def _out_of_scope(sub: IdeaSubmission) -> str | None:
    """ "advert" or "off_topic" when a team's own submission is not an idea for the programme, else None."""
    text = " ".join(getattr(sub, f) for f in SCOPE_FIELDS)
    if len({m.group(0).lower() for m in vocabulary.ADVERT.finditer(text)}) >= vocabulary.MIN_ADVERT_WORDS:
        return "advert"
    on_topic = vocabulary.OCEAN.search(text) or any(
        area_words(text, area, english) for area, english in impact_areas(sub.preset).items()
    )
    return None if on_topic else "off_topic"


def _tier(
    potential: PotentialBand,
    evidence: EvidenceBand,
    results: list[CriterionResult],
    *,
    stop: str | None,
    public_record: bool,
) -> tuple[Tier, str]:
    """stop: why the idea is held back before its bands count (held, low effort, out of scope), or None."""
    if stop:
        return "not_yet", TIER_REASONS[stop]
    if potential == "unknown":
        return ("ask_two", TIER_REASONS["unknown_public"]) if public_record else ("not_yet", TIER_REASONS["unknown"])
    impact = next(r for r in results if r.id == "impact")
    if potential == "high" and evidence in ("some", "strong") and (impact.rung or 0) >= 2:
        return "bring_now", (
            f"High potential, {evidence} evidence and an impact area shown in the text: worth A'Pelago's time now."
        )
    if potential == "high" or (potential == "medium" and evidence != "thin"):
        return "ask_two", f"{potential.capitalize()} potential and {evidence} evidence: two answers would decide it."
    return "not_yet", TIER_REASONS["medium_thin" if potential == "medium" else "low"]


def gap_order(results: list[CriterionResult]) -> list[CriterionResult]:
    """The criteria whose answer would most change the read: blanks first, then thin evidence, then weak
    answers; heavier criteria first within each group."""
    by_weight = sorted(results, key=lambda r: -r.weight)
    blanks = [r for r in by_weight if r.axis == "potential" and r.rung is None]
    thin = [r for r in by_weight if r.axis == "evidence" and (r.rung or 0) <= 1]
    weak = [r for r in by_weight if r.axis == "potential" and r.rung is not None and r.rung <= 1]
    return blanks + thin + weak


def _questions(results: list[CriterionResult], extra: tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys([*extra, *(r.question for r in gap_order(results))]))[:2]


def _strengths(results: list[CriterionResult]) -> list[str]:
    strong = sorted((r for r in results if (r.rung or 0) >= 2 and r.id != "trace"), key=lambda r: -r.weight)
    return [strength(r.label, r.rung_label) + (f' ("{r.quote}")' if r.quote else "") for r in strong[:3]]


def strength(label: str, rung_label: str) -> str:
    """A strength without the team's quote: "Problem and who has it: Says who has it"."""
    return f"{label}: {rung_label}"


def _claims_ledger(sub: IdeaSubmission, claims: list[Claim], source: str) -> list[LedgerItem]:
    items = [
        LedgerItem(
            id=f"claim:{c.signal}",
            field=c.field,
            state="claim",
            text=SIGNALS[c.signal].text if c.signal in SIGNALS else "Shows how it helps the impact area",
            quote=c.quote,
            source=source + (" (found by the model)" if c.by == "model" else ""),
        )
        for c in claims
    ]
    form = "Your form answers" if source == "Your submission" else source
    items += [
        LedgerItem(id=f"form:{e}", field="exists", state="claim", text=f"Has: {EXISTS_LABELS[e].lower()}", source=form)
        for e in sub.exists
    ]
    if sub.impact_area:
        items.append(
            LedgerItem(
                id="form:impact", field="impact", state="claim", source=form, text=f"Impact area: {sub.impact_area}"
            )
        )
    if sub.team:
        held = {m.role for m in sub.team}
        roles = ", ".join(label for role, label in ROLE_LABELS.items() if role in held)  # one fixed order
        items.append(
            LedgerItem(
                id="form:team", field="team", state="claim", source=form, text=f"Team of {len(sub.team)}: {roles}"
            )
        )
    if sub.commitment:
        items.append(
            LedgerItem(
                id="form:commitment",
                field="team",
                state="claim",
                source=form,
                text=f"Time on the idea: {sub.commitment.replace('_', ' ')}",
            )
        )
    return items


def _assumptions(
    sub: IdeaSubmission, inferred: dict[str, list[str]], s: dict[str, Claim], flags: list[Flag]
) -> list[LedgerItem]:
    # The team's own pick is a claim (see _claims_ledger); an area the text also points to never replaces it.
    label = "Also touches" if sub.impact_area else "Impact area"
    out = [
        LedgerItem(
            id=f"assume:area:{i}",
            field="impact",
            state="assumption",
            text=f"{label}: {area}",
            quote=", ".join(hits),
            source="BlueWatch rules",
            basis=f"Inferred from the quoted {'word' if len(hits) == 1 else 'words'} in the text",
        )
        for i, (area, hits) in enumerate(inferred.items())
    ]
    if "built" in s and not {"prototype", "pilot"} & set(sub.exists):
        out.append(
            LedgerItem(
                id="assume:built",
                field="exists",
                state="assumption",
                source="BlueWatch rules",
                text="Something may already be built",
                quote=s["built"].quote,
                basis="The text mentions it, but the form does not list a prototype or pilot",
            )
        )
        flags.append(Flag(kind="form_text_mismatch", text="The text mentions something built; the form does not."))
    return out


def _unknowns(results: list[CriterionResult]) -> list[LedgerItem]:
    return [
        LedgerItem(
            id=f"unknown:{r.id}",
            field=r.id,
            state="unknown",
            text=f"{r.label}: not stated",
            source="BlueWatch rules",
            next_check=NextCheck(kind="ask_founder", question=r.question),
        )
        for r in results
        if r.rung is None or (r.axis == "evidence" and r.rung == 0)
    ]
