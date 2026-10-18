"""Idea Harbour contracts: what a team submits, what the vetting returns, and A'Pelago's review queue.

Local to this module (not in bluewatch/models.py) so the shared contracts stay untouched; the shared
shapes are reused where they fit (NextCheck, Route, ShareConsent). The TypeScript mirror is
frontend/src/screens/ideas/types.ts, kept in step by tests/ideas/test_ts_types.py.

The public form collects no names, e-mail addresses or phone numbers: team members are roles and skills.
Every text field has a hard size limit, so a request can never carry more than a few kilobytes.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from bluewatch.models import Model, NextCheck, Route, ShareConsent

LIMITS = {
    "title": 80,
    "problem": 600,
    "who_has_it": 300,
    "solution": 800,
    "who_pays": 300,
    "exists_detail": 500,
    "skills": 80,
    "link": 200,
    "team": 6,
    "links": 3,
}

Role = Literal["build", "business", "domain", "design"]
Exists = Literal[
    "research", "concept", "prototype", "pilot", "user_interviews", "letters_of_intent", "paying_customers"
]
Need = Literal["mentors", "pilot_partner", "funding", "team", "test_access"]
Commitment = Literal["full_time", "part_time", "side_project"]
TeamCountry = Literal["FI", "SE", "NO", "EE", "DK", "other"]
PresetName = Literal["blue", "climate_circular"]

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _text(limit: int, minimum: int = 0):
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=minimum, max_length=limit)]


Title = _text(LIMITS["title"], 3)
Problem = _text(LIMITS["problem"])
WhoHasIt = _text(LIMITS["who_has_it"])
Solution = _text(LIMITS["solution"])
WhoPays = _text(LIMITS["who_pays"])
AreaName = _text(LIMITS["title"])
ExistsDetail = _text(LIMITS["exists_detail"])
Skills = _text(LIMITS["skills"])
Link = _text(LIMITS["link"])


class TeamMember(Model):
    role: Role
    skills: Skills = ""  # "marine biology MSc", "embedded C"; never a name


class IdeaSubmission(Model):
    title: Title
    problem: Problem = ""
    who_has_it: WhoHasIt = ""
    solution: Solution = ""
    who_pays: WhoPays = ""
    impact_area: AreaName | None = None  # one of the preset's area names; None = "not sure"
    exists: list[Exists] = Field(default_factory=list, max_length=7)
    exists_detail: ExistsDetail = ""
    needs: list[Need] = Field(default_factory=list, max_length=5)
    team: list[TeamMember] = Field(default_factory=list, max_length=LIMITS["team"])
    commitment: Commitment | None = None
    country: TeamCountry | None = None
    links: list[Link] = Field(default_factory=list, max_length=LIMITS["links"])
    preset: PresetName = "blue"
    # The team's own choice, per submission: True lets Claude read the answers too (the text goes to
    # Anthropic's API for this read only). False, the default when a client says nothing, means rules only.
    ai_read: bool = False

    @field_validator("title", "problem", "who_has_it", "solution", "who_pays", "exists_detail", mode="before")
    @classmethod
    def _plain_text(cls, value: object) -> object:
        """Unicode-normalised, control characters removed; newlines and tabs stay."""
        return _CONTROL.sub("", unicodedata.normalize("NFKC", value)) if isinstance(value, str) else value

    @field_validator("exists", "needs")
    @classmethod
    def _unique(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @field_validator("links")
    @classmethod
    def _web_links(cls, value: list[str]) -> list[str]:
        for link in value:
            if not re.fullmatch(r"https?://[^\s<>\"']+", link):
                raise ValueError("Links must be full web addresses starting with https://")
        return value


# --------------------------------------------------------------------------- what the vetting reads
ClaimField = Literal["problem", "who_has_it", "solution", "who_pays", "exists_detail"]


class Claim(Model):
    """One signal in the team's own words: the quote is copied exactly from the named field."""

    field: ClaimField
    signal: str
    quote: str
    by: Literal["rules", "model"] = "rules"


Axis = Literal["potential", "evidence"]
PotentialBand = Literal["high", "medium", "low", "unknown"]
EvidenceBand = Literal["strong", "some", "thin"]
Tier = Literal["bring_now", "ask_two", "not_yet"]
Reader = Literal["rules", "rules_and_model"]


class CriterionResult(Model):
    id: str
    label: str
    axis: Axis
    weight: int
    rung: int | None = None  # 0-3; None = not stated (left out of potential, counts as nothing for evidence)
    rung_label: str
    rule: str  # how this criterion is decided, in plain words
    quote: str | None = None  # the words that decided it
    question: str  # what A'Pelago would ask to settle it


LedgerState = Literal["fact", "claim", "assumption", "unknown"]


class LedgerItem(Model):
    id: str
    field: str
    state: LedgerState  # fact = public record; claim = the team's own words; assumption = our inference
    text: str
    quote: str | None = None
    source: str  # "Your submission", "Organiser's results page", "CORDIS project record", "BlueWatch rules"
    source_url: str | None = None
    basis: str | None = None  # why an assumption is made
    next_check: NextCheck | None = None


class IdeaLedger(Model):
    facts: list[LedgerItem] = Field(default_factory=list)
    claims: list[LedgerItem] = Field(default_factory=list)
    assumptions: list[LedgerItem] = Field(default_factory=list)
    unknowns: list[LedgerItem] = Field(default_factory=list)


StepKind = Literal["check", "programme", "proof_step", "funding", "invite"]


class IdeaStep(Model):
    rank: int
    kind: StepKind
    title: str
    action: str
    why: str
    status: str | None = None  # "Applications open", "2027 dates not announced", ...
    deadline: date | None = None
    source_url: str | None = None
    instrument_id: str | None = None  # an id in data/seed/grants.json; never invented


FlagKind = Literal[
    "low_effort",
    "held_instructions",
    "contact_details_removed",
    "grant_dependency",
    "personal_link_dropped",
    "near_duplicate",
    "form_text_mismatch",
]


class Flag(Model):
    kind: FlagKind
    text: str


class SimilarItem(Model):
    id: str
    title: str
    source: str


class IdeaAssessment(Model):
    id: str  # a hash of the submission: the same text always gets the same id
    title: str
    preset: str
    tier: Tier
    tier_label: str
    tier_rule: str  # the rule that decided the tier, in plain words
    potential: PotentialBand
    evidence: EvidenceBand
    potential_rule: str
    evidence_rule: str
    criteria: list[CriterionResult]
    strengths: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)  # the two to ask (or to answer next)
    ledger: IdeaLedger
    next_steps: list[IdeaStep] = Field(default_factory=list)
    funding_note: str = ""
    impact_areas: list[str] = Field(default_factory=list)  # tags only, never a numeric impact level
    stage: str  # furthest stage stated: "Idea", "Research", "Concept", "Prototype", "Pilot"
    needs: list[Need] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)
    similar_to: list[SimilarItem] = Field(default_factory=list)
    reader: Reader = "rules"
    reader_note: str = ""  # which reader, and why the model was not used when it was asked for
    rubric_version: str
    stored: bool = False


# --------------------------------------------------------------------------- A'Pelago's review queue
OriginKind = Literal["your_submission", "hackathon_result", "research_project"]


class Origin(Model):
    kind: OriginKind
    label: str  # "Your submission (this browser session)", "Public hackathon result", "Sample submission (invented)"
    url: str | None = None
    checked: str | None = None  # "Checked 17 Oct 2026"
    facts: list[str] = Field(default_factory=list)


class Invite(Model):
    """How A'Pelago reaches a team it found in public data: through an organisation, never a person."""

    route: Route
    message: str  # the text the organisation is asked to forward
    note: str  # that sending is off: nothing is sent


class QueueItem(Model):
    rank: int
    id: str
    origin: Origin
    assessment: IdeaAssessment
    why_here: list[str]
    invite: Invite | None = None
    in_top: bool = False
    duplicate_of: str | None = None


class IdeaQueue(Model):
    mode: Literal["apelago", "redstone"]
    preset: str
    generated_at: datetime
    top_n: int
    top_ids: list[str]  # at most top_n; never padded
    why_these: str
    why_not_next: str | None = None
    items: list[QueueItem]
    counts: dict[str, int] = Field(default_factory=dict)  # by tier and by source
    facets: dict[str, dict[str, int]] = Field(default_factory=dict)  # stage, impact_area, need, source
    session_items: int = 0
    base_rate_note: str
    sample: bool = False  # True only for the sample-data preview: every item is an invented idea
    sample_label: str | None = None  # what the samples are, shown with them


# --------------------------------------------------------------------------- form, consent, rubric
class ShareRequest(Model):
    submission: IdeaSubmission
    consent: bool
    consent_text_version: str


class ShareReceipt(Model):
    demo: bool
    stored: Literal["session_memory", "file"]
    expires_at: datetime | None = None
    item_id: str
    consent: ShareConsent
    message: str


class WithdrawReceipt(Model):
    removed: int
    message: str


class SessionShares(Model):
    """What this browser session has shared and not withdrawn, so the student page can always offer Withdraw."""

    count: int
    expires_at: datetime | None = None


class Option(Model):
    value: str
    label: str
    hint: str = ""


class IdeaForm(Model):
    preset: str
    impact_areas: list[Option]
    exists: list[Option]
    needs: list[Option]
    roles: list[Option]
    commitment: list[Option]
    countries: list[Option]
    limits: dict[str, int]
    consent_text: str
    consent_text_version: str
    privacy_note: str
    model_reading: bool  # the server can let Claude read (flag and key); the team still chooses per submission
    ai_read_text: str  # the label of the "Claude may read our answers too" toggle (default on in the UI)
    ai_read_off_note: str  # shown under the toggle when model_reading is false; empty otherwise


class RubricCriterion(Model):
    id: str
    label: str
    axis: Axis
    weight: int
    rungs: list[str]  # rung 0-3 labels
    rule: str
    question: str


class RubricInfo(Model):
    version: str
    criteria: list[RubricCriterion]
    potential_rule: str
    evidence_rule: str
    tier_rules: list[str]
    anti_gaming: list[str]
