// Filtering the company table: one text filter plus multi-select facets, each counted against the other
// active filters so a count always says how many rows that choice would show.
import type { CompanyRow } from "../../contracts";

export type FacetKey = "country" | "group" | "vertical" | "match" | "listed";
export type Selection = Record<FacetKey, string[]>;

export const FACETS: FacetKey[] = ["country", "group", "vertical", "match", "listed"];
export const NO_SELECTION: Selection = {
  country: [],
  group: [],
  vertical: [],
  match: [],
  listed: [],
};

export const UNKNOWN = "unknown";
export const LISTED = "listed";

/** Two capital letters are a country; anything else the set holds ("XX", "DK_VAT") is unknown. */
export function countryKey(code: string): string {
  return /^[A-Z]{2}$/.test(code) && code !== "XX" ? code : UNKNOWN;
}

export function facetValue(key: FacetKey, row: CompanyRow, listedIds: Set<string>): string {
  switch (key) {
    case "country":
      return countryKey(row.country);
    case "group":
      return row.group;
    case "vertical":
      return row.vertical ?? UNKNOWN;
    case "match":
      return row.resolution;
    case "listed":
      return listedIds.has(row.id) ? LISTED : "not_listed";
  }
}

const compact = (s: string) => s.toLowerCase().replace(/[\s.-]/g, "");

/** Name or business ID, with or without the dash and spaces ("3652359-1", "36523591", "938 525 420"). */
export function matchesText(row: CompanyRow, text: string): boolean {
  const q = text.trim().toLowerCase();
  if (!q) return true;
  return row.name.toLowerCase().includes(q) || compact(row.registry_id).includes(compact(q));
}

function passes(
  row: CompanyRow,
  selection: Selection,
  listedIds: Set<string>,
  except?: FacetKey,
): boolean {
  return FACETS.every(
    (key) =>
      key === except ||
      selection[key].length === 0 ||
      selection[key].includes(facetValue(key, row, listedIds)),
  );
}

export function applyFilters(
  rows: CompanyRow[],
  text: string,
  selection: Selection,
  listedIds: Set<string>,
): CompanyRow[] {
  return rows.filter((r) => matchesText(r, text) && passes(r, selection, listedIds));
}

/** How many rows each value of one facet would show, given the text and every other facet. */
export function facetCounts(
  rows: CompanyRow[],
  key: FacetKey,
  text: string,
  selection: Selection,
  listedIds: Set<string>,
): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of rows) {
    if (!matchesText(row, text) || !passes(row, selection, listedIds, key)) continue;
    const value = facetValue(key, row, listedIds);
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return counts;
}

export function selectedCount(selection: Selection): number {
  return FACETS.reduce((n, key) => n + selection[key].length, 0);
}
