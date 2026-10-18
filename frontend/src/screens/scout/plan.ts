// What the scout reads from a plan, in the interface language: its score parts, its flags, the placement
// and place, and a title when the project is missing. Called while rendering, by components that re-render on a language switch.
import type { ContactPlan, ScoutProject } from "../../contracts";
import { localeOf, translator } from "../../i18n/messages";
import type { Tone } from "../../ui/Chip";
import type { ScorePart } from "../../ui/ScoreBar";
import { scoutMessages } from "./messages";

export type CompanyStatus = NonNullable<ScoutProject["company_status"]>;

export const STATUS_TONES: Record<CompanyStatus, Tone> = {
  none_found: "blue",
  already_a_company: "grey",
  check: "hatch",
};

const PART_KEYS = [
  "placement",
  "event_size",
  "partner_on_jury",
  "theme_fit",
  "recency",
  "prototype",
  "pre_company",
  "organiser_offers_support",
] as const;
type PartKey = (typeof PART_KEYS)[number];

const isPartKey = (key: string): key is PartKey => (PART_KEYS as readonly string[]).includes(key);

/** Every part the API sends a ceiling for, in the API's order. */
export function scoreParts(plan: ContactPlan): ScorePart[] {
  const { t } = translator(scoutMessages);
  const { parts = {}, maxima = {} } = plan.promise_score;
  return Object.entries(parts).flatMap(([key, value]) =>
    key in maxima
      ? [{ key, label: isPartKey(key) ? t(`part_${key}`) : key, value, max: maxima[key] }]
      : [],
  );
}

export interface Flag {
  kind: "warm" | "dualUse";
  label: string;
  detail: string;
  tone: Tone;
}

// The plan builder (bluewatch/scout/plans.py) writes its flags in English: "Warm route: {partner} sat on
// the jury" and "Dual use: …". Only these two become chips; the others repeat what the company-status
// chip and the notes already say.
const WARM_ROUTE = /^Warm route: (.+) sat on the jury$/;

export function planFlags(plan: ContactPlan): Flag[] {
  const { t } = translator(scoutMessages);
  return (plan.flags ?? []).flatMap((text): Flag[] => {
    const warm = WARM_ROUTE.exec(text);
    if (warm) {
      const detail = t("flag_warmDetail", { partner: warm[1] });
      return [{ kind: "warm", label: t("flag_warm"), detail, tone: "teal" }];
    }
    if (text.startsWith("Dual use:")) {
      const detail = t("flag_dualUseDetail");
      return [{ kind: "dualUse", label: t("flag_dualUse"), detail, tone: "amber" }];
    }
    return [];
  });
}

/** The result as a short label in the interface language: "Winner", "Voittaja", "Vinnare". */
export function placementLabel(project: ScoutProject): string {
  const { t } = translator(scoutMessages);
  return t(`placement_${project.placement ?? "listed"}`);
}

/** "Klaipėda, Lithuania" in the interface language: the country is named from its ISO code. */
export function projectPlace(project: ScoutProject): string {
  const { t } = translator(scoutMessages);
  const code = project.country_code;
  const country = code ? new Intl.DisplayNames([localeOf()], { type: "region" }).of(code) : null;
  return [project.online ? t("online") : project.city, country].filter(Boolean).join(", ");
}

/** "ku-exe" -> "Ku exe": a readable stand-in when the plan came without its project. */
function fromSlug(slug: string): string {
  const words = slug.replace(/-/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function projectTitle(plan: ContactPlan): string {
  return plan.project?.team_or_project ?? fromSlug(plan.project_id.split("/").pop() ?? "");
}

export function projectEvent(plan: ContactPlan): string {
  return plan.project?.event ?? fromSlug(plan.project_id.split("/")[0]);
}

/** The event without its bracketed aside, for one-line rows: "Ocean Hackathon (Campus …)" -> "Ocean Hackathon". */
export function shortEvent(plan: ContactPlan): string {
  return projectEvent(plan).replace(/\s*\(.*$/, "");
}

/** A second guard behind the backend's minors rule (bluewatch/scout/projects.py): a youth or school event
 * is never shown, also when the organiser's own headline in the source URL says "youths". */
export function isYouthOrSchoolEvent(plan: ContactPlan): boolean {
  return (
    /\b(young|youths?|school)\b/i.test(projectEvent(plan)) ||
    /\byouths?\b/i.test(plan.project?.source_url ?? "")
  );
}
