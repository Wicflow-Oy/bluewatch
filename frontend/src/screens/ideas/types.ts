// Idea Harbour API types: a hand-written mirror of bluewatch/ideas/models.py (not generated, so the
// shared contracts.ts stays untouched). tests/ideas/test_ts_types.py fails if a field drifts.
// Requests mark fields with server defaults optional; responses always carry every field.
import type { NextCheck, Route, ShareConsent } from "../../contracts";

export type Role = "build" | "business" | "domain" | "design";
export type Exists =
  | "research"
  | "concept"
  | "prototype"
  | "pilot"
  | "user_interviews"
  | "letters_of_intent"
  | "paying_customers";
export type Need = "mentors" | "pilot_partner" | "funding" | "team" | "test_access";
export type Commitment = "full_time" | "part_time" | "side_project";
export type TeamCountry = "FI" | "SE" | "NO" | "EE" | "DK" | "other";
export type PresetName = "blue" | "climate_circular";
export type Tier = "bring_now" | "ask_two" | "not_yet";
export type Reader = "rules" | "rules_and_model";
export type PotentialBand = "high" | "medium" | "low" | "unknown";
export type EvidenceBand = "strong" | "some" | "thin";
export type LedgerState = "fact" | "claim" | "assumption" | "unknown";
export type StepKind = "check" | "programme" | "proof_step" | "funding" | "invite";
export type FlagKind =
  | "low_effort"
  | "held_instructions"
  | "contact_details_removed"
  | "grant_dependency"
  | "personal_link_dropped"
  | "near_duplicate"
  | "form_text_mismatch";
export type OriginKind = "your_submission" | "hackathon_result" | "research_project";

// --- request
export interface TeamMember {
  role: Role;
  /** "marine biology MSc", "embedded C": never a name. */
  skills?: string;
}

export interface IdeaSubmission {
  title: string;
  problem?: string;
  who_has_it?: string;
  solution?: string;
  who_pays?: string;
  /** One of IdeaForm.impact_areas, or null for "Not sure". */
  impact_area?: string | null;
  exists?: Exists[];
  exists_detail?: string;
  needs?: Need[];
  team?: TeamMember[];
  commitment?: Commitment | null;
  country?: TeamCountry | null;
  links?: string[];
  preset?: PresetName;
  /** The team's choice from the "Claude may read our answers too" toggle (on by default in the UI). */
  ai_read?: boolean;
}

export interface ShareRequest {
  submission: IdeaSubmission;
  consent: boolean;
  consent_text_version: string;
}

// --- the readiness read
export interface CriterionResult {
  id: string;
  label: string;
  axis: "potential" | "evidence";
  weight: number;
  /** 0-3; null = not stated (left out of potential, nothing shown for evidence). */
  rung: number | null;
  rung_label: string;
  rule: string;
  quote: string | null;
  question: string;
}

export interface LedgerItem {
  id: string;
  field: string;
  state: LedgerState;
  text: string;
  quote: string | null;
  source: string;
  source_url: string | null;
  basis: string | null;
  next_check: NextCheck | null;
}

export interface IdeaLedger {
  facts: LedgerItem[];
  claims: LedgerItem[];
  assumptions: LedgerItem[];
  unknowns: LedgerItem[];
}

export interface IdeaStep {
  rank: number;
  kind: StepKind;
  title: string;
  action: string;
  why: string;
  status: string | null;
  /** ISO date. */
  deadline: string | null;
  source_url: string | null;
  instrument_id: string | null;
}

export interface Flag {
  kind: FlagKind;
  text: string;
}

export interface SimilarItem {
  id: string;
  title: string;
  source: string;
}

export interface IdeaAssessment {
  id: string;
  title: string;
  preset: string;
  tier: Tier;
  tier_label: string;
  tier_rule: string;
  potential: PotentialBand;
  evidence: EvidenceBand;
  potential_rule: string;
  evidence_rule: string;
  criteria: CriterionResult[];
  strengths: string[];
  questions: string[];
  ledger: IdeaLedger;
  next_steps: IdeaStep[];
  funding_note: string;
  /** Tags only, never a numeric impact level. */
  impact_areas: string[];
  stage: string;
  needs: Need[];
  flags: Flag[];
  similar_to: SimilarItem[];
  reader: Reader;
  /** Which reader made this read, and why Claude did not when it was asked to. Always show it. */
  reader_note: string;
  rubric_version: string;
  stored: boolean;
}

// --- A'Pelago's review queue
export interface Origin {
  kind: OriginKind;
  label: string;
  url: string | null;
  checked: string | null;
  facts: string[];
}

export interface Invite {
  route: Route;
  message: string;
  note: string;
}

export interface QueueItem {
  rank: number;
  id: string;
  origin: Origin;
  assessment: IdeaAssessment;
  why_here: string[];
  invite: Invite | null;
  in_top: boolean;
  duplicate_of: string | null;
}

export interface IdeaQueue {
  mode: "apelago" | "redstone";
  preset: string;
  generated_at: string;
  top_n: number;
  top_ids: string[];
  why_these: string;
  why_not_next: string | null;
  items: QueueItem[];
  counts: Record<string, number>;
  /** stage, impact_area, need, source, tier: value -> count. */
  facets: Record<string, Record<string, number>>;
  session_items: number;
  base_rate_note: string;
  /** True only for the sample-data preview: every item is an invented idea. */
  sample: boolean;
  /** What the samples are, shown with them; null in the live queue. */
  sample_label: string | null;
}

// --- form, consent, rubric
export interface Option {
  value: string;
  label: string;
  hint: string;
}

export interface IdeaForm {
  preset: string;
  impact_areas: Option[];
  exists: Option[];
  needs: Option[];
  roles: Option[];
  commitment: Option[];
  countries: Option[];
  limits: Record<string, number>;
  consent_text: string;
  consent_text_version: string;
  privacy_note: string;
  /** The server can let Claude read (the team still chooses per submission). */
  model_reading: boolean;
  /** The toggle's label, shown next to the submit button. */
  ai_read_text: string;
  /** Shown under the toggle when model_reading is false; empty otherwise. */
  ai_read_off_note: string;
}

export interface ShareReceipt {
  demo: boolean;
  stored: "session_memory" | "file";
  expires_at: string | null;
  item_id: string;
  consent: ShareConsent;
  message: string;
}

export interface WithdrawReceipt {
  removed: number;
  message: string;
}

/** What this browser session has shared and not withdrawn (GET /api/ideas/shared). */
export interface SessionShares {
  count: number;
  expires_at: string | null;
}

export interface RubricCriterion {
  id: string;
  label: string;
  axis: "potential" | "evidence";
  weight: number;
  /** What rung 0, 1, 2 and 3 mean. */
  rungs: string[];
  rule: string;
  question: string;
}

export interface RubricInfo {
  version: string;
  criteria: RubricCriterion[];
  potential_rule: string;
  evidence_rule: string;
  tier_rules: string[];
  anti_gaming: string[];
}
