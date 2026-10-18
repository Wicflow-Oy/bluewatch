// Pure reads of the funding catalogue (/api/funding): instruments x this week's listed companies.
// The screen looks at one company at a time, so everything here turns that matrix into one company's view.
import type { FundingCatalogue, FundingInstrument, FundingTierRow } from "../../contracts";
import { daysUntil } from "../../lib/format";
import { stepKindLabel } from "../../lib/labels";
import type { Tier, TierItem } from "../../ui/TierGroup";

export type Kind = FundingInstrument["kind"];

export interface CompanyOption {
  id: string;
  name: string;
}

export interface FundingItem extends TierItem {
  kind: Kind;
}

export type DeadlineWindow = "any" | "14" | "30" | "90";

export interface Filters {
  kind: Kind | "all";
  window: DeadlineWindow;
  /** A tier key; items match by the tier's word in the current workspace (A'Pelago words two tiers "Likely"). */
  tier: Tier | "all";
}

export const NO_FILTERS: Filters = { kind: "all", window: "any", tier: "all" };

/** The listed companies in list order, named as the catalogue names them. */
export function companiesOf(catalogue: FundingCatalogue): CompanyOption[] {
  const byId = new Map<string, CompanyOption>();
  for (const instrument of catalogue.instruments) {
    for (const row of instrument.tiers ?? []) {
      if (!byId.has(row.company_id))
        byId.set(row.company_id, { id: row.company_id, name: row.name });
    }
  }
  return catalogue.company_ids.flatMap((id) => byId.get(id) ?? []);
}

const isUpcoming = (deadline: string | null | undefined, today: string) =>
  !!deadline && (daysUntil(deadline, today) ?? -1) >= 0;

/** The first listed company with an open, dated grant it isn't excluded from: the page opens on a live case. */
export function defaultCompanyId(
  catalogue: FundingCatalogue,
  companies: CompanyOption[],
): string | null {
  const datedGrants = catalogue.instruments.filter(
    (i) => i.kind === "grant" && isUpcoming(i.deadline, catalogue.today),
  );
  const hasDatedGrant = (companyId: string) =>
    datedGrants.some((i) =>
      i.tiers?.some((t) => t.company_id === companyId && t.tier !== "excluded"),
    );
  return (companies.find((c) => hasDatedGrant(c.id)) ?? companies[0])?.id ?? null;
}

function toItem(instrument: FundingInstrument, row: FundingTierRow): FundingItem {
  return {
    id: instrument.id,
    name: instrument.name,
    kind: instrument.kind,
    tier: row.tier,
    rule: row.deciding_rule,
    // The catalogue's rules come from the instrument's own page; the founder view names the same URL.
    ruleSource: instrument.url,
    ruleVerified: row.rule_verified,
    deadline: instrument.deadline,
    upgradePath: row.upgrade_path,
    unknownReason: row.unknown_reason,
    detail: [stepKindLabel(instrument.kind), instrument.funder].filter(Boolean).join(" · "),
    deadlineNote: instrument.deadline_note,
    checks: row.checks,
  };
}

/** Upcoming deadlines first (soonest first), then undated, then closed. */
function deadlineRank(item: FundingItem, today: string): [number, number] {
  if (!item.deadline) return [1, 0];
  const days = daysUntil(item.deadline, today) ?? 0;
  return days >= 0 ? [0, days] : [2, -days];
}

export function itemsFor(catalogue: FundingCatalogue, companyId: string): FundingItem[] {
  const rank = (item: FundingItem) => deadlineRank(item, catalogue.today);
  return catalogue.instruments
    .flatMap((instrument) => {
      const row = instrument.tiers?.find((t) => t.company_id === companyId);
      return row ? [toItem(instrument, row)] : [];
    })
    .sort((a, b) => {
      const [ga, da] = rank(a);
      const [gb, db] = rank(b);
      return ga - gb || da - db || a.name.localeCompare(b.name);
    });
}

export function inWindow(item: FundingItem, window: DeadlineWindow, today: string): boolean {
  if (window === "any") return true;
  const days = item.deadline ? daysUntil(item.deadline, today) : null;
  return days !== null && days >= 0 && days <= Number(window);
}

export function applyFilters(
  items: FundingItem[],
  filters: Filters,
  today: string,
  tierWord: (tier: Tier) => string,
): FundingItem[] {
  const wantedWord = filters.tier === "all" ? null : tierWord(filters.tier);
  return items.filter(
    (item) =>
      (filters.kind === "all" || item.kind === filters.kind) &&
      inWindow(item, filters.window, today) &&
      (wantedWord === null || tierWord(item.tier) === wantedWord),
  );
}

// ---- the SBEP call 4 flip: two fixed reference companies, one registered in Finland, one in Norway

export const FLIP_LEFT_ID = "FI:3652359-1"; // Meriva Oy
export const FLIP_RIGHT_ID = "NO:938525420"; // HAVNIO AS

export interface Flip {
  call: FundingInstrument | null;
  left: FundingTierRow | null;
  right: FundingTierRow | null;
}

export function sbepFlip(catalogue: FundingCatalogue): Flip {
  const call = catalogue.instruments.find((i) => i.id.includes("sbep")) ?? null;
  const rowOf = (companyId: string) => call?.tiers?.find((t) => t.company_id === companyId) ?? null;
  return { call, left: rowOf(FLIP_LEFT_ID), right: rowOf(FLIP_RIGHT_ID) };
}
