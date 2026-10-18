"""BlueWatch contracts: the only shared interface between modules.

C1 Signal, C2 Company, C3 Evidence, C4 Assessment/Opportunity/ListEntry, C5 Outreach,
C6 PrecisionReport, C7 Bridge, C8 HackathonProject/ContactPlan, C9 FounderProfile/FounderView,
plus investors and the venture card.

When this file changes, bump CONTRACTS_VERSION, update tests/test_contracts.py and regenerate
frontend/src/contracts.ts with scripts/gen_ts_types.py in the same commit.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACTS_VERSION = "2.3.0"

_Date = date

Mode = Literal["apelago", "redstone"]
Country = str  # ISO 3166-1 alpha-2, upper case: FI, NO, EE, SE, ...


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- C1 Signal
SignalSource = Literal[
    "prh",
    "brreg",
    "rik",
    "scb",
    "krek",
    "ted",
    "cordis",
    "interreg",
    "sedia",
    "crtsh",
    "vies",
    "site",
    "hackathon",
    "manual",
]
SignalType = Literal[
    "newly_founded",
    "share_issue",
    "award",
    "open_tender",
    "eu_project",
    "eu_grant_signed",
    "new_hostname",
    "call_open",
    "project_published",
    "site_change",
]
RegistryName = Literal["prh", "brreg", "rik", "scb", "vies"]


class EntityRef(Model):
    registry: RegistryName | None = None
    id: str | None = None
    project_url: str | None = None
    name: str | None = None  # as printed by the source; never used alone for matching


class Signal(Model):
    id: str
    source: SignalSource
    type: SignalType
    entity_ref: EntityRef
    event_date: date | None = None
    first_seen_at: datetime
    url: str | None = None
    hash: str
    sensitivity: Literal["public", "founder_sensitive"] = "public"
    title: str | None = None
    payload: dict = Field(default_factory=dict)  # source-specific: CPV, NACE, deadline, ...


SourceState = Literal["live", "daily_file", "weekly_file", "cached", "unavailable", "planned"]


class SourceStatus(Model):
    source: str  # prh | brreg | rik | ted | cordis | interreg | ...
    label: str  # "Finland company register (PRH)"
    state: SourceState
    checked_at: datetime | None = None
    data_as_of: datetime | None = None
    records: int | None = None
    detail: str = ""  # e.g. "timed out; not counted as zero"


# --------------------------------------------------------------------------- C2 Company
class Registry(Model):
    country: Country
    id: str
    name: str | None = None
    founded: date | None = None
    form: str | None = None  # OY, AS, OU, AB, ...
    industry_code: str | None = None  # TOL/NACE/EMTAK/SNI; None while not yet assigned
    industry_scheme: str | None = None
    municipality: str | None = None
    website: str | None = None
    status: str | None = None
    natural_person: bool = False  # sole traders: never ranked, never contacted
    employees: int | None = None  # as the register states it; None when it does not


class ConnectorResult(Model):
    signals: list[Signal] = Field(default_factory=list)
    records: list[Registry] = Field(default_factory=list)
    status: SourceStatus


class Candidate(Model):
    name: str
    registry: Registry
    score: float
    reason: str


ResolutionState = Literal["resolved", "probable", "ambiguous", "unconfirmed", "unresolved"]


class Resolution(Model):
    state: ResolutionState
    reason: str
    candidates: list[Candidate] = Field(default_factory=list)


Vertical = Literal[
    "maritime_ports",
    "ocean_infra_clean_energy",
    "marine_intelligence",
    "blue_biotech_water",
    "other",
]


class Company(Model):
    id: str  # "FI:3652359-1", "NO:938525420", "EE:16123456"
    names: list[str]
    registry: Registry
    domain: str | None = None
    vertical: Vertical | None = None
    vertical_note: str | None = None  # "workboats", "marina software", ...
    resolution: Resolution
    signal_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    vat_id: str | None = None
    one_liner: str | None = None  # plain description, quoted or paraphrased from evidence


# --------------------------------------------------------------------------- C3 Evidence
EvidenceState = Literal["fact", "assumption", "unknown", "not_applicable"]
EvidenceTag = Literal[
    "read",
    "sedia",
    "registry",
    "site",
    "llm",
    "ted",
    "cordis",
    "snippet",
    "dossier",
    "company_reply",
]


class NextCheck(Model):
    kind: Literal["public_check", "ask_founder"]
    how: str | None = None
    question: str | None = None
    due: date | None = None


class Confirmation(Model):
    by: Literal["company_reply"]
    at: datetime
    draft_id: str | None = None


class Evidence(Model):
    id: str
    company_id: str | None = None
    project_id: str | None = None
    field: str  # founded, product, team, customers, pricing, funding, public_contracts, impact, ...
    claim: str
    value: str | None = None
    quote: str | None = None  # exact page text; site/llm claims need verified_quote=True to count
    url: str | None = None
    event_date: date | None = None
    first_seen_at: datetime | None = None
    retrieved_at: datetime | None = None
    source_family: str  # syndicated copies count once: "ted", "prh", "site:havnio.no", ...
    tag: EvidenceTag
    verified_quote: bool = False
    state: EvidenceState = "fact"
    basis: str | None = None  # for assumptions
    why_unknown: str | None = None  # for unknown / not_applicable
    next_check: NextCheck | None = None
    confirmed_by: Confirmation | None = None


class GapLedger(Model):
    company_id: str
    facts: list[Evidence] = Field(default_factory=list)
    assumptions: list[Evidence] = Field(default_factory=list)
    unknowns: list[Evidence] = Field(default_factory=list)
    not_applicable: list[Evidence] = Field(default_factory=list)


# --------------------------------------------------------------------------- C4 Assessment
LevelKey = Literal["trl", "brl", "oirl", "irl"]
Confidence = Literal["low", "medium", "high"]


class ReadinessLevel(Model):
    key: LevelKey
    level: int | None = None  # None = unknown; never 0 for unknown
    band: str | None = None  # "1-3", "4-6", "7-9", or a word
    confidence: Confidence = "low"
    evidence_ids: list[str] = Field(default_factory=list)
    unknown_reason: str | None = None
    raise_by: str | None = None  # the evidence that would raise the level
    applicable: bool = True
    areas: list[str] = Field(default_factory=list)  # oirl: Ocean Impact Navigator area tags
    thesis_quote: str | None = None  # oirl: the company's own impact thesis (its claim)


DimensionKey = Literal[
    "market",
    "product",
    "team",
    "business_model",
    "competition",
    "marketing_distribution",
    "financials",
    "tech",
    "deal_dynamics",
    "impact",
]
DIMENSIONS: tuple[str, ...] = (
    "market",
    "product",
    "team",
    "business_model",
    "competition",
    "marketing_distribution",
    "financials",
    "tech",
    "deal_dynamics",
    "impact",
)


class DimensionState(Model):
    key: DimensionKey
    state: EvidenceState
    evidence_ids: list[str] = Field(default_factory=list)
    note: str | None = None


Group = Literal["act_now", "dive_deeper", "not_yet", "not_for_us"]


class Score(Model):
    potential: float  # 0..1
    evidence: float  # 0..1; unknowns lower only this axis
    group: Group
    potential_parts: dict[str, float] = Field(default_factory=dict)
    evidence_parts: dict[str, float] = Field(default_factory=dict)
    explanation: list[str] = Field(default_factory=list)


class Assessment(Model):
    company_id: str
    levels: list[ReadinessLevel]
    dimensions: list[DimensionState]
    flags: list[str] = Field(default_factory=list)
    score: Score
    rules_version: str
    preset: str = "blue"
    assessed_at: datetime


OpportunityKind = Literal["programme", "ask_company", "grant", "investor", "buyer", "partner", "pilot"]
# A step can also be the register-match check that comes before any contact; it is never an opportunity.
StepKind = Literal[OpportunityKind, "confirm_match"]
Tier = Literal["certain", "likely", "possible", "excluded", "unknown"]


class Opportunity(Model):
    id: str
    company_id: str
    kind: OpportunityKind
    ref_id: str | None = None  # instrument, investor, partner or bridge id
    title: str
    tier: Tier = "unknown"
    rule: str | None = None  # the deciding rule in plain words
    rule_source: str | None = None
    rule_verified: bool = False  # only read/sedia rules may produce "certain"
    deadline: date | None = None
    upgrade_path: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    why: list[str] = Field(default_factory=list)
    action: str
    priority: float = 0.0  # higher first; reproducible from priority_parts
    priority_parts: dict[str, float] = Field(default_factory=dict)


class NextStep(Model):
    rank: int
    opportunity_id: str
    kind: StepKind
    title: str
    action: str
    why: str = ""
    deadline: date | None = None
    audience: Literal["ecosystem_actor", "startup", "both"] = "both"


class Reason(Model):
    text: str
    evidence_id: str | None = None
    source_label: str
    url: str | None = None
    event_date: date | None = None
    first_seen_at: datetime | None = None
    retrieved_at: datetime | None = None


Chip = Literal["newly_founded", "newly_active", "new_to_list"]


class ListEntry(Model):  # one row of the shortlist
    rank: int
    company_id: str
    name: str
    country: Country
    founded: date | None = None
    vertical: Vertical | None = None
    vertical_note: str | None = None
    chip: Chip
    group: Group
    reasons: list[Reason]  # three where available
    next_action: str
    deadline: date | None = None
    change: str | None = None  # "new since you last looked", "changed: ..."
    modes: list[Mode]
    score: Score
    rank_parts: dict[str, float] = Field(default_factory=dict)


class ShortList(Model):
    mode: Mode
    preset: str
    generated_at: datetime
    entries: list[ListEntry]  # at most `cap`; never padded
    cap: int = 10
    why_these: str
    why_not_next: str | None = None
    since: datetime | None = None
    sources: list[SourceStatus] = Field(default_factory=list)
    rules_version: str


class Alert(Model):
    id: str
    company_id: str
    trigger: str
    priority: Literal["high", "medium", "low"]
    reasons: list[str]
    evidence_ids: list[str] = Field(default_factory=list)
    next_action: str
    deadline: date | None = None
    status: Literal["new", "seen", "done", "dismissed"] = "new"
    created_at: datetime
    opportunity_id: str | None = None  # deadline alerts: the company's Opportunity.id
    title: str | None = None  # the instrument or signal; companies sharing one deadline share its title


# --------------------------------------------------------------------------- investors
class Investor(Model):
    id: str
    name: str
    type: str
    hq_country: str | None = None
    stages: list[str] = Field(default_factory=list)
    ticket_eur_min: int | None = None
    ticket_eur_max: int | None = None
    thesis_keywords: list[str] = Field(default_factory=list)
    ocean_portfolio: list[str] = Field(default_factory=list)
    website: str | None = None
    source_urls: list[str] = Field(default_factory=list)
    verification: str = "name-only"  # read | read+snippet | snippet | name-only
    exclude_from_matching: bool = False
    status: str | None = None
    kind: Literal["vc", "cvc", "angel_network", "public", "impact_fund", "accelerator", "other"] = "other"


class InvestorMatch(Model):
    investor_id: str
    name: str
    rank: int
    score: float
    parts: dict[str, float] = Field(default_factory=dict)
    fit_label: str  # "Fit: stage, ocean transport, Norway" / "Partial fit" / "Not now"
    why: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    verification: str = "name-only"
    when: Literal["now", "later", "not_a_fit"] = "later"


# --------------------------------------------------------------------------- C5 Outreach
ChannelKind = Literal["org_generic", "org_press", "contact_form", "named_role", "opt_in", "personal_blocked"]


class Channel(Model):
    kind: ChannelKind
    address: str | None = None  # organisation addresses only; personal addresses are never stored
    source_url: str | None = None
    role_check_evidence_id: str | None = None


class Question(Model):
    text: str
    evidence_id: str  # the unknown it would close


class AuditEvent(Model):
    at: datetime
    actor: str
    action: str
    detail: str = ""


DraftStatus = Literal[
    "draft",
    "pending_approval",
    "approved",
    "rejected",
    "sent",
    "blocked_demo",
    "blocked_suppressed",
    "replied",
    "bounced",
    "opted_out",
]


class OutreachDraft(Model):
    id: str
    company_id: str | None = None
    project_id: str | None = None
    mode: Literal["first_touch", "evidence_request"]
    channel: Channel
    subject: str
    body: str
    language: Literal["fi", "sv", "en", "no", "et"] = "en"
    bridge_id: str | None = None
    opportunity_ref: str | None = None
    questions: list[Question] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    risk: Literal["low", "high"] = "low"
    status: DraftStatus = "draft"
    approver: str | None = None
    approved_at: datetime | None = None
    approved_text_hash: str | None = None
    lawful_route: Literal["org_generic", "role_authorised", "consent"] | None = None
    demo_recipient: str | None = None  # the team inbox demo mode actually used
    audit: list[AuditEvent] = Field(default_factory=list)


class PolicyDecision(Model):
    allowed: bool
    route: str | None = None
    reasons: list[str] = Field(default_factory=list)


class Reply(Model):
    draft_id: str
    received_at: datetime
    from_domain: str
    classification: Literal["answer", "not_interested", "opt_out", "bounce", "other"]
    snippet: str = ""  # short; bodies are not stored
    confirms_evidence_ids: list[str] = Field(default_factory=list)


class BriefSentence(Model):
    text: str
    evidence_ids: list[str]


class Brief(Model):
    company_id: str
    sentences: list[BriefSentence]


# --------------------------------------------------------------------------- C6 Precision
class LevelAgreement(Model):
    key: LevelKey
    n: int
    exact: int
    within_one: int
    weighted_kappa: float | None = None
    confusion: dict[str, dict[str, int]] = Field(default_factory=dict)
    baseline_name: str = "age baseline"
    baseline_exact: int | None = None
    baseline_within_one: int | None = None


class TrapResult(Model):
    case: str
    expected: str
    got: str
    passed: bool
    note: str = ""


class PrecisionReport(Model):
    generated_at: datetime
    rules_hash: str
    frozen_at: datetime | None = None
    blind: bool = False
    reference: str = ""  # which answer set was used
    levels: list[LevelAgreement] = Field(default_factory=list)
    traps: list[TrapResult] = Field(default_factory=list)
    classifier_precision: float | None = None
    classifier_recall: float | None = None
    classifier_n: int | None = None
    bridges_verified_share: float | None = None
    gap_closure: dict[str, int] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- C7 Bridge
BridgeType = Literal[
    "won_before_open_again",
    "already_works_with",
    "rule_decides",
    "proof_step",
    "law_creates_buyer",
    "programme_fit",
    "lab_window",
]


class BridgeParty(Model):
    name: str
    kind: str | None = None
    country: Country | None = None
    registry_id: str | None = None
    company_id: str | None = None


class BridgeEvidence(Model):
    claim: str
    url: str | None = None
    date: str | None = None  # partial dates allowed ("2026-06")
    deadline: _Date | None = None  # _Date: the field "date" shadows the type inside this class
    end: _Date | None = None
    tag: str


class Bridge(Model):
    id: str
    type: BridgeType
    company: BridgeParty
    counterparty: BridgeParty
    reason: str
    evidence_company: list[BridgeEvidence]
    evidence_counterparty: list[BridgeEvidence]
    deadline: date | None = None
    action: str
    confidence: Literal["verified", "probable", "possible"]
    caveat: str | None = None
    mode: Literal["apelago", "redstone", "both"] = "both"
    anonymised_name: str | None = None  # stands in for the company when a viewer hides names
    # Other words that name the company (a project acronym, a research organisation, a product name),
    # hidden with its name
    identifying_terms: list[str] = Field(default_factory=list)
    rank_parts: dict[str, float] = Field(default_factory=dict)
    generator: str = "seed"  # "seed" or the generator's name


# --------------------------------------------------------------------------- C8 Hackathon scout
class HackathonProject(Model):
    id: str
    event: str
    edition: str | None = None
    date: str | None = None
    city: str | None = None
    country: str | None = None
    organiser: str | None = None
    placement: str | None = None
    team_or_project: str
    idea: str | None = None
    source_url: str | None = None
    tag: str | None = None
    company_status: Literal["already_a_company", "none_found", "check"] = "check"
    minors_likely: bool = False
    in_window: bool = True
    meta: dict = Field(default_factory=dict)


# A result in five classes, worst last: the organiser's own wording, with our research notes, stays in the seed.
PlacementClass = Literal["1st", "2nd", "3rd", "finalist_or_award", "listed"]


class ScoutProject(Model):
    """What the organiser published about a project, as served to the browser: facts the interface can show
    in any language. HackathonProject.meta and the seed's wording hold research notes, so the API sends this."""

    id: str
    team_or_project: str
    event: str
    year: int | None = None  # of the result; None when the results page gives no date
    city: str | None = None
    country_code: str | None = None  # ISO 3166-1 alpha-2; the interface names the country in its language
    online: bool = False
    placement: PlacementClass = "listed"
    idea: str | None = None
    source_url: str | None = None
    company_status: Literal["already_a_company", "none_found", "check"] = "check"


class PromiseScore(Model):
    total: float
    parts: dict[str, float] = Field(default_factory=dict)
    maxima: dict[str, float] = Field(default_factory=dict)  # each part's ceiling; together they make 100


RouteKind = Literal["organiser", "warm_intro", "university_office", "team_public_channel", "event", "opt_in"]


class Route(Model):
    rank: int
    kind: RouteKind
    organisation: str
    how: str
    contact_page_url: str | None = None


class ContactPlanDraft(Model):
    to_route_rank: int
    subject: str
    points: list[str]


class ContactPlan(Model):
    project_id: str
    mode: Literal["first_touch", "evidence_request"] = "evidence_request"
    promise_score: PromiseScore
    gaps: list[Evidence] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    offer: str | None = None
    offer_bridge_id: str | None = None
    route_ladder: list[Route] = Field(default_factory=list)
    draft: ContactPlanDraft | None = None
    status: Literal["planned", "draft", "pending_approval", "sent_demo", "replied", "opted_in", "closed"] = "planned"
    flags: list[str] = Field(default_factory=list)
    project: ScoutProject | None = None
    # There is deliberately no field for a person's name or contact details.


# --------------------------------------------------------------------------- C9 Founder view
class FounderProfile(Model):
    id: str
    business_id: str | None = None
    country: Country
    name: str | None = None  # the company's name, never a person's
    founded: date | None = None
    size_band: Literal["micro", "small", "medium", "large", "unknown"] = "unknown"
    org_type: Literal["company", "research_org", "student_team", "individual_founding"] = "company"
    trl_band: str | None = None
    themes: list[str] = Field(default_factory=list)
    source: Literal["register", "self_reported"] = "register"


class FounderTier(Model):
    instrument_id: str
    instrument_name: str
    tier: Tier
    deciding_rule: str
    rule_source: str | None = None
    rule_verified: bool = False
    deadline: date | None = None
    upgrade_path: str | None = None
    unknown_reason: str | None = None


class ShareConsent(Model):
    given: bool
    scope: list[str] = Field(default_factory=list)
    consent_text_version: str
    given_at: datetime | None = None
    withdrawn_at: datetime | None = None


class FounderView(Model):
    profile: FounderProfile
    tiers: list[FounderTier] = Field(default_factory=list)
    programmes: list[Opportunity] = Field(default_factory=list)
    investors: list[InvestorMatch] = Field(default_factory=list)
    next_30_days: list[NextStep] = Field(default_factory=list)
    share_consent: ShareConsent | None = None
    rules_version: str


# --------------------------------------------------------------------------- venture card
class VentureCard(Model):
    company: Company
    assessment: Assessment
    ledger: GapLedger
    evidence: list[Evidence] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)
    investors: list[InvestorMatch] = Field(default_factory=list)
    bridges: list[Bridge] = Field(default_factory=list)
    next_steps: list[NextStep] = Field(default_factory=list)
    sources: list[SourceStatus] = Field(default_factory=list)


# --------------------------------------------------------------------------- API views
# Read-only shapes the screens need beyond the contracts above. Every number in them is computed by the
# rules; nothing here is a new source of truth.
class CompanyRow(Model):
    """One company in the precomputed set, compact, for the Companies page and the command palette."""

    id: str
    name: str
    country: Country
    registry_id: str
    founded: date | None = None
    vertical: Vertical | None = None
    vertical_note: str | None = None
    tags: list[str] = Field(default_factory=list)
    resolution: ResolutionState
    group: Group
    potential: float
    evidence: float
    next_action: str | None = None
    deadline: date | None = None


class PresetInfo(Model):
    name: str
    label: str
    description: str


class PublishedRule(Model):
    field: str  # country_rule, consortium_rule, applicant_types, ...
    text: str
    source_tag: str  # read | sedia | snippet | inferred | unverified
    verified: bool  # read on the official page (read or sedia)


class FundingCheck(Model):
    name: str
    outcome: Literal["pass", "fail", "unknown"]
    text: str
    source_tag: str
    verified: bool


class FundingTierRow(Model):
    company_id: str
    name: str
    country: Country
    tier: Tier
    deciding_rule: str
    rule_verified: bool
    upgrade_path: str | None = None
    unknown_reason: str | None = None
    checks: list[FundingCheck] = Field(default_factory=list)


class FundingInstrument(Model):
    id: str
    name: str
    funder: str | None = None
    type: str
    kind: OpportunityKind
    status: str
    deadline: date | None = None
    deadline_note: str | None = None
    url: str | None = None
    themes: list[str] = Field(default_factory=list)
    rules: list[PublishedRule] = Field(default_factory=list)
    tiers: list[FundingTierRow] = Field(default_factory=list)


class FundingCatalogue(Model):
    mode: Mode
    today: date
    rules_version: str
    company_ids: list[str]  # the shortlisted companies each instrument is tiered for
    instruments: list[FundingInstrument]


class DeskDraft(Model):
    """An outreach draft with the hash an approval must quote and the policy's plain-words decision."""

    draft: OutreachDraft
    text_hash: str
    decision: PolicyDecision


class DeskReply(Model):
    draft: DeskDraft
    reply: Reply
    confirmed: list[Evidence]  # the unknowns the reply turned into facts confirmed by the company
