// UI wording for contract enums, in the interface language. Group, tier, level and dimension labels come
// from /api/meta, translated by the API (bluewatch/labels.py); these are the words for everything else.
// Accessors read the current language when called, and a language switch re-renders the whole app.
import type {
  Bridge,
  Evidence,
  ListEntry,
  NextStep,
  Opportunity,
  SourceStatus,
} from "../contracts";
import type { Mode } from "../api";
import { translator } from "../i18n/messages";
import { labelMessages } from "./messages";

export type Group = ListEntry["group"];
export type BridgeType = Bridge["type"];
export type Vertical = NonNullable<ListEntry["vertical"]>;

export const GROUP_ORDER: Group[] = ["act_now", "dive_deeper", "not_yet", "not_for_us"];

export const VERTICALS: Vertical[] = [
  "maritime_ports",
  "ocean_infra_clean_energy",
  "marine_intelligence",
  "blue_biotech_water",
  "other",
];

export const STEP_KINDS: Opportunity["kind"][] = [
  "programme",
  "ask_company",
  "grant",
  "investor",
  "buyer",
  "partner",
  "pilot",
];

type LabelKey = keyof typeof labelMessages.en;
const t = (key: LabelKey) => translator(labelMessages).t(key);

export function chipLabel(chip: ListEntry["chip"]): string {
  return t(`chip_${chip}`);
}

export function verticalLabel(vertical: Vertical): string {
  return t(`vertical_${vertical}`);
}

/** "Maritime and ports (marina software)"; an "other" vertical is described by its note alone. */
export function verticalText(vertical: ListEntry["vertical"], note?: string | null): string | null {
  if (!vertical) return note ?? null;
  if (vertical === "other") return note ?? verticalLabel("other");
  if (!note) return verticalLabel(vertical);
  return translator(labelMessages).t("verticalWithNote", {
    vertical: verticalLabel(vertical),
    note,
  });
}

export function stepKindLabel(kind: NextStep["kind"]): string {
  return t(`step_${kind}`);
}

export function bridgeType(type: BridgeType): { label: string; explainer: string } {
  return { label: t(`bridge_${type}`), explainer: t(`bridge_${type}_explainer`) };
}

export function confidenceLabel(confidence: Bridge["confidence"]): string {
  return t(`confidence_${confidence}`);
}

/** Spec 2.3: a snapshot we read earlier is "recorded"; "cached" is our plumbing, not the reader's. */
export function sourceStateLabel(state: SourceStatus["state"]): string {
  return t(`source_${state}`);
}

const EVIDENCE_FAMILIES = [
  "prh",
  "prh_notices",
  "brreg",
  "rik",
  "ted",
  "cordis",
  "crtsh",
  "research_pack",
  "company_reply",
  "hackathon_results",
  "regulation",
] as const;
type EvidenceFamily = (typeof EVIDENCE_FAMILIES)[number];

function isEvidenceFamily(family: string): family is EvidenceFamily {
  return (EVIDENCE_FAMILIES as readonly string[]).includes(family);
}

/** Who said it, in words. null for a gap-ledger entry: an unknown has no source to cite. */
export function evidenceSourceLabel(evidence: Pick<Evidence, "source_family">): string | null {
  const family = evidence.source_family;
  const words = translator(labelMessages);
  if (family === "gap_ledger") return null;
  if (family.startsWith("site:"))
    return words.t("evidenceCompanySite", { host: family.slice("site:".length) });
  // The outreach desk records a confirmed fact as "company_reply:{sender domain}".
  if (family.startsWith("company_reply:"))
    return words.t("evidenceCompanyReplyFrom", { domain: family.slice("company_reply:".length) });
  return isEvidenceFamily(family) ? t(`evidence_${family}`) : words.t("evidenceOther", { family });
}

/** "Finland company register (PRH)" -> "PRH"; labels without an acronym stay whole. */
export function shortSourceName(label: string): string {
  const m = /\(([^)]+)\)\s*$/.exec(label);
  return m ? m[1] : label;
}

const COUNTRIES = ["FI", "NO", "EE", "SE", "DK"] as const;

/** The country's name in the interface language; an unknown code stays as it is. */
export function countryName(code: string): string {
  const known = COUNTRIES.find((c) => c === code);
  return known ? t(`country_${known}`) : code;
}

/** Workspace names are product names and stay untranslated; their kind is a word. */
export const WORKSPACES = {
  apelago: { name: "A'Pelago", initial: "A" },
  redstone: { name: "Redstone", initial: "R" },
} as const;

export function workspaceKind(mode: Mode): string {
  return t(`workspace_${mode}`);
}
