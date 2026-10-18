// Generated from bluewatch/models.py by scripts/gen_ts_types.py. Do not edit by hand.
export const CONTRACTS_VERSION = "2.3.0";

export interface Alert {
  id: string;
  company_id: string;
  trigger: string;
  priority: "high" | "medium" | "low";
  reasons: string[];
  evidence_ids?: string[];
  next_action: string;
  deadline?: string | null;
  status?: "new" | "seen" | "done" | "dismissed";
  created_at: string;
  opportunity_id?: string | null;
  title?: string | null;
}

export interface Assessment {
  company_id: string;
  levels: ReadinessLevel[];
  dimensions: DimensionState[];
  flags?: string[];
  score: Score;
  rules_version: string;
  preset?: string;
  assessed_at: string;
}

export interface AuditEvent {
  at: string;
  actor: string;
  action: string;
  detail?: string;
}

export interface Bridge {
  id: string;
  type: "won_before_open_again" | "already_works_with" | "rule_decides" | "proof_step" | "law_creates_buyer" | "programme_fit" | "lab_window";
  company: BridgeParty;
  counterparty: BridgeParty;
  reason: string;
  evidence_company: BridgeEvidence[];
  evidence_counterparty: BridgeEvidence[];
  deadline?: string | null;
  action: string;
  confidence: "verified" | "probable" | "possible";
  caveat?: string | null;
  mode?: "apelago" | "redstone" | "both";
  anonymised_name?: string | null;
  identifying_terms?: string[];
  rank_parts?: Record<string, number>;
  generator?: string;
}

export interface BridgeEvidence {
  claim: string;
  url?: string | null;
  date?: string | null;
  deadline?: string | null;
  end?: string | null;
  tag: string;
}

export interface BridgeParty {
  name: string;
  kind?: string | null;
  country?: string | null;
  registry_id?: string | null;
  company_id?: string | null;
}

export interface Brief {
  company_id: string;
  sentences: BriefSentence[];
}

export interface BriefSentence {
  text: string;
  evidence_ids: string[];
}

export interface Candidate {
  name: string;
  registry: Registry;
  score: number;
  reason: string;
}

export interface Channel {
  kind: "org_generic" | "org_press" | "contact_form" | "named_role" | "opt_in" | "personal_blocked";
  address?: string | null;
  source_url?: string | null;
  role_check_evidence_id?: string | null;
}

export interface Company {
  id: string;
  names: string[];
  registry: Registry;
  domain?: string | null;
  vertical?: "maritime_ports" | "ocean_infra_clean_energy" | "marine_intelligence" | "blue_biotech_water" | "other" | null;
  vertical_note?: string | null;
  resolution: Resolution;
  signal_ids?: string[];
  tags?: string[];
  vat_id?: string | null;
  one_liner?: string | null;
}

export interface CompanyRow {
  id: string;
  name: string;
  country: string;
  registry_id: string;
  founded?: string | null;
  vertical?: "maritime_ports" | "ocean_infra_clean_energy" | "marine_intelligence" | "blue_biotech_water" | "other" | null;
  vertical_note?: string | null;
  tags?: string[];
  resolution: "resolved" | "probable" | "ambiguous" | "unconfirmed" | "unresolved";
  group: "act_now" | "dive_deeper" | "not_yet" | "not_for_us";
  potential: number;
  evidence: number;
  next_action?: string | null;
  deadline?: string | null;
}

export interface Confirmation {
  by: "company_reply";
  at: string;
  draft_id?: string | null;
}

export interface ConnectorResult {
  signals?: Signal[];
  records?: Registry[];
  status: SourceStatus;
}

export interface ContactPlan {
  project_id: string;
  mode?: "first_touch" | "evidence_request";
  promise_score: PromiseScore;
  gaps?: Evidence[];
  questions?: string[];
  offer?: string | null;
  offer_bridge_id?: string | null;
  route_ladder?: Route[];
  draft?: ContactPlanDraft | null;
  status?: "planned" | "draft" | "pending_approval" | "sent_demo" | "replied" | "opted_in" | "closed";
  flags?: string[];
  project?: ScoutProject | null;
}

export interface ContactPlanDraft {
  to_route_rank: number;
  subject: string;
  points: string[];
}

export interface DeskDraft {
  draft: OutreachDraft;
  text_hash: string;
  decision: PolicyDecision;
}

export interface DeskReply {
  draft: DeskDraft;
  reply: Reply;
  confirmed: Evidence[];
}

export interface DimensionState {
  key: "market" | "product" | "team" | "business_model" | "competition" | "marketing_distribution" | "financials" | "tech" | "deal_dynamics" | "impact";
  state: "fact" | "assumption" | "unknown" | "not_applicable";
  evidence_ids?: string[];
  note?: string | null;
}

export interface EntityRef {
  registry?: "prh" | "brreg" | "rik" | "scb" | "vies" | null;
  id?: string | null;
  project_url?: string | null;
  name?: string | null;
}

export interface Evidence {
  id: string;
  company_id?: string | null;
  project_id?: string | null;
  field: string;
  claim: string;
  value?: string | null;
  quote?: string | null;
  url?: string | null;
  event_date?: string | null;
  first_seen_at?: string | null;
  retrieved_at?: string | null;
  source_family: string;
  tag: "read" | "sedia" | "registry" | "site" | "llm" | "ted" | "cordis" | "snippet" | "dossier" | "company_reply";
  verified_quote?: boolean;
  state?: "fact" | "assumption" | "unknown" | "not_applicable";
  basis?: string | null;
  why_unknown?: string | null;
  next_check?: NextCheck | null;
  confirmed_by?: Confirmation | null;
}

export interface FounderProfile {
  id: string;
  business_id?: string | null;
  country: string;
  name?: string | null;
  founded?: string | null;
  size_band?: "micro" | "small" | "medium" | "large" | "unknown";
  org_type?: "company" | "research_org" | "student_team" | "individual_founding";
  trl_band?: string | null;
  themes?: string[];
  source?: "register" | "self_reported";
}

export interface FounderTier {
  instrument_id: string;
  instrument_name: string;
  tier: "certain" | "likely" | "possible" | "excluded" | "unknown";
  deciding_rule: string;
  rule_source?: string | null;
  rule_verified?: boolean;
  deadline?: string | null;
  upgrade_path?: string | null;
  unknown_reason?: string | null;
}

export interface FounderView {
  profile: FounderProfile;
  tiers?: FounderTier[];
  programmes?: Opportunity[];
  investors?: InvestorMatch[];
  next_30_days?: NextStep[];
  share_consent?: ShareConsent | null;
  rules_version: string;
}

export interface FundingCatalogue {
  mode: "apelago" | "redstone";
  today: string;
  rules_version: string;
  company_ids: string[];
  instruments: FundingInstrument[];
}

export interface FundingCheck {
  name: string;
  outcome: "pass" | "fail" | "unknown";
  text: string;
  source_tag: string;
  verified: boolean;
}

export interface FundingInstrument {
  id: string;
  name: string;
  funder?: string | null;
  type: string;
  kind: "programme" | "ask_company" | "grant" | "investor" | "buyer" | "partner" | "pilot";
  status: string;
  deadline?: string | null;
  deadline_note?: string | null;
  url?: string | null;
  themes?: string[];
  rules?: PublishedRule[];
  tiers?: FundingTierRow[];
}

export interface FundingTierRow {
  company_id: string;
  name: string;
  country: string;
  tier: "certain" | "likely" | "possible" | "excluded" | "unknown";
  deciding_rule: string;
  rule_verified: boolean;
  upgrade_path?: string | null;
  unknown_reason?: string | null;
  checks?: FundingCheck[];
}

export interface GapLedger {
  company_id: string;
  facts?: Evidence[];
  assumptions?: Evidence[];
  unknowns?: Evidence[];
  not_applicable?: Evidence[];
}

export interface HackathonProject {
  id: string;
  event: string;
  edition?: string | null;
  date?: string | null;
  city?: string | null;
  country?: string | null;
  organiser?: string | null;
  placement?: string | null;
  team_or_project: string;
  idea?: string | null;
  source_url?: string | null;
  tag?: string | null;
  company_status?: "already_a_company" | "none_found" | "check";
  minors_likely?: boolean;
  in_window?: boolean;
  meta?: Record<string, unknown>;
}

export interface Investor {
  id: string;
  name: string;
  type: string;
  hq_country?: string | null;
  stages?: string[];
  ticket_eur_min?: number | null;
  ticket_eur_max?: number | null;
  thesis_keywords?: string[];
  ocean_portfolio?: string[];
  website?: string | null;
  source_urls?: string[];
  verification?: string;
  exclude_from_matching?: boolean;
  status?: string | null;
  kind?: "vc" | "cvc" | "angel_network" | "public" | "impact_fund" | "accelerator" | "other";
}

export interface InvestorMatch {
  investor_id: string;
  name: string;
  rank: number;
  score: number;
  parts?: Record<string, number>;
  fit_label: string;
  why?: string[];
  caveats?: string[];
  verification?: string;
  when?: "now" | "later" | "not_a_fit";
}

export interface LevelAgreement {
  key: "trl" | "brl" | "oirl" | "irl";
  n: number;
  exact: number;
  within_one: number;
  weighted_kappa?: number | null;
  confusion?: Record<string, Record<string, number>>;
  baseline_name?: string;
  baseline_exact?: number | null;
  baseline_within_one?: number | null;
}

export interface ListEntry {
  rank: number;
  company_id: string;
  name: string;
  country: string;
  founded?: string | null;
  vertical?: "maritime_ports" | "ocean_infra_clean_energy" | "marine_intelligence" | "blue_biotech_water" | "other" | null;
  vertical_note?: string | null;
  chip: "newly_founded" | "newly_active" | "new_to_list";
  group: "act_now" | "dive_deeper" | "not_yet" | "not_for_us";
  reasons: Reason[];
  next_action: string;
  deadline?: string | null;
  change?: string | null;
  modes: ("apelago" | "redstone")[];
  score: Score;
  rank_parts?: Record<string, number>;
}

export interface NextCheck {
  kind: "public_check" | "ask_founder";
  how?: string | null;
  question?: string | null;
  due?: string | null;
}

export interface NextStep {
  rank: number;
  opportunity_id: string;
  kind: "programme" | "ask_company" | "grant" | "investor" | "buyer" | "partner" | "pilot" | "confirm_match";
  title: string;
  action: string;
  why?: string;
  deadline?: string | null;
  audience?: "ecosystem_actor" | "startup" | "both";
}

export interface Opportunity {
  id: string;
  company_id: string;
  kind: "programme" | "ask_company" | "grant" | "investor" | "buyer" | "partner" | "pilot";
  ref_id?: string | null;
  title: string;
  tier?: "certain" | "likely" | "possible" | "excluded" | "unknown";
  rule?: string | null;
  rule_source?: string | null;
  rule_verified?: boolean;
  deadline?: string | null;
  upgrade_path?: string | null;
  evidence_ids?: string[];
  why?: string[];
  action: string;
  priority?: number;
  priority_parts?: Record<string, number>;
}

export interface OutreachDraft {
  id: string;
  company_id?: string | null;
  project_id?: string | null;
  mode: "first_touch" | "evidence_request";
  channel: Channel;
  subject: string;
  body: string;
  language?: "fi" | "sv" | "en" | "no" | "et";
  bridge_id?: string | null;
  opportunity_ref?: string | null;
  questions?: Question[];
  evidence_ids?: string[];
  risk?: "low" | "high";
  status?: "draft" | "pending_approval" | "approved" | "rejected" | "sent" | "blocked_demo" | "blocked_suppressed" | "replied" | "bounced" | "opted_out";
  approver?: string | null;
  approved_at?: string | null;
  approved_text_hash?: string | null;
  lawful_route?: "org_generic" | "role_authorised" | "consent" | null;
  demo_recipient?: string | null;
  audit?: AuditEvent[];
}

export interface PolicyDecision {
  allowed: boolean;
  route?: string | null;
  reasons?: string[];
}

export interface PrecisionReport {
  generated_at: string;
  rules_hash: string;
  frozen_at?: string | null;
  blind?: boolean;
  reference?: string;
  levels?: LevelAgreement[];
  traps?: TrapResult[];
  classifier_precision?: number | null;
  classifier_recall?: number | null;
  classifier_n?: number | null;
  bridges_verified_share?: number | null;
  gap_closure?: Record<string, number>;
  notes?: string[];
}

export interface PresetInfo {
  name: string;
  label: string;
  description: string;
}

export interface PromiseScore {
  total: number;
  parts?: Record<string, number>;
  maxima?: Record<string, number>;
}

export interface PublishedRule {
  field: string;
  text: string;
  source_tag: string;
  verified: boolean;
}

export interface Question {
  text: string;
  evidence_id: string;
}

export interface ReadinessLevel {
  key: "trl" | "brl" | "oirl" | "irl";
  level?: number | null;
  band?: string | null;
  confidence?: "low" | "medium" | "high";
  evidence_ids?: string[];
  unknown_reason?: string | null;
  raise_by?: string | null;
  applicable?: boolean;
  areas?: string[];
  thesis_quote?: string | null;
}

export interface Reason {
  text: string;
  evidence_id?: string | null;
  source_label: string;
  url?: string | null;
  event_date?: string | null;
  first_seen_at?: string | null;
  retrieved_at?: string | null;
}

export interface Registry {
  country: string;
  id: string;
  name?: string | null;
  founded?: string | null;
  form?: string | null;
  industry_code?: string | null;
  industry_scheme?: string | null;
  municipality?: string | null;
  website?: string | null;
  status?: string | null;
  natural_person?: boolean;
  employees?: number | null;
}

export interface Reply {
  draft_id: string;
  received_at: string;
  from_domain: string;
  classification: "answer" | "not_interested" | "opt_out" | "bounce" | "other";
  snippet?: string;
  confirms_evidence_ids?: string[];
}

export interface Resolution {
  state: "resolved" | "probable" | "ambiguous" | "unconfirmed" | "unresolved";
  reason: string;
  candidates?: Candidate[];
}

export interface Route {
  rank: number;
  kind: "organiser" | "warm_intro" | "university_office" | "team_public_channel" | "event" | "opt_in";
  organisation: string;
  how: string;
  contact_page_url?: string | null;
}

export interface Score {
  potential: number;
  evidence: number;
  group: "act_now" | "dive_deeper" | "not_yet" | "not_for_us";
  potential_parts?: Record<string, number>;
  evidence_parts?: Record<string, number>;
  explanation?: string[];
}

export interface ScoutProject {
  id: string;
  team_or_project: string;
  event: string;
  year?: number | null;
  city?: string | null;
  country_code?: string | null;
  online?: boolean;
  placement?: "1st" | "2nd" | "3rd" | "finalist_or_award" | "listed";
  idea?: string | null;
  source_url?: string | null;
  company_status?: "already_a_company" | "none_found" | "check";
}

export interface ShareConsent {
  given: boolean;
  scope?: string[];
  consent_text_version: string;
  given_at?: string | null;
  withdrawn_at?: string | null;
}

export interface ShortList {
  mode: "apelago" | "redstone";
  preset: string;
  generated_at: string;
  entries: ListEntry[];
  cap?: number;
  why_these: string;
  why_not_next?: string | null;
  since?: string | null;
  sources?: SourceStatus[];
  rules_version: string;
}

export interface Signal {
  id: string;
  source: "prh" | "brreg" | "rik" | "scb" | "krek" | "ted" | "cordis" | "interreg" | "sedia" | "crtsh" | "vies" | "site" | "hackathon" | "manual";
  type: "newly_founded" | "share_issue" | "award" | "open_tender" | "eu_project" | "eu_grant_signed" | "new_hostname" | "call_open" | "project_published" | "site_change";
  entity_ref: EntityRef;
  event_date?: string | null;
  first_seen_at: string;
  url?: string | null;
  hash: string;
  sensitivity?: "public" | "founder_sensitive";
  title?: string | null;
  payload?: Record<string, unknown>;
}

export interface SourceStatus {
  source: string;
  label: string;
  state: "live" | "daily_file" | "weekly_file" | "cached" | "unavailable" | "planned";
  checked_at?: string | null;
  data_as_of?: string | null;
  records?: number | null;
  detail?: string;
}

export interface TrapResult {
  case: string;
  expected: string;
  got: string;
  passed: boolean;
  note?: string;
}

export interface VentureCard {
  company: Company;
  assessment: Assessment;
  ledger: GapLedger;
  evidence?: Evidence[];
  opportunities?: Opportunity[];
  investors?: InvestorMatch[];
  bridges?: Bridge[];
  next_steps?: NextStep[];
  sources?: SourceStatus[];
}
