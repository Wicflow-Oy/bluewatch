// Client-side filters over the queue: any value within a group, every group at once. Filters hide rows;
// they never renumber the ranks the rubric gave.
import type { QueueItem } from "./types";

export const FACET_KEYS = ["source", "tier", "stage", "impact_area", "need"] as const;

export type FacetKey = (typeof FACET_KEYS)[number];
export type Filters = Record<FacetKey, string[]>;
export type FacetCounts = Record<FacetKey, [value: string, count: number][]>;

export const NO_FILTERS: Filters = { source: [], tier: [], stage: [], impact_area: [], need: [] };

function valuesOf(item: QueueItem, key: FacetKey): string[] {
  const read = item.assessment;
  switch (key) {
    case "source":
      return [item.origin.kind];
    case "tier":
      return [read.tier];
    case "stage":
      return [read.stage];
    case "impact_area":
      return read.impact_areas;
    case "need":
      return read.needs;
  }
}

/**
 * Each group's values and counts, in rank order of first appearance. Counted from the items rather than
 * taken from IdeaQueue.facets: the API translates an item's stage and impact areas, but not the facet
 * keys, so in Finnish or Swedish the server's keys would never match an item.
 */
export function facetCounts(items: QueueItem[]): FacetCounts {
  const counts = Object.fromEntries(FACET_KEYS.map((key) => [key, new Map<string, number>()]));
  for (const item of items) {
    for (const key of FACET_KEYS) {
      for (const value of valuesOf(item, key)) {
        counts[key].set(value, (counts[key].get(value) ?? 0) + 1);
      }
    }
  }
  return Object.fromEntries(
    FACET_KEYS.map((key) => [key, [...counts[key].entries()]]),
  ) as FacetCounts;
}

export function matches(item: QueueItem, filters: Filters): boolean {
  return FACET_KEYS.every((key) => {
    const wanted = filters[key];
    return wanted.length === 0 || valuesOf(item, key).some((v) => wanted.includes(v));
  });
}

export function activeCount(filters: Filters): number {
  return FACET_KEYS.reduce((n, key) => n + filters[key].length, 0);
}

/**
 * The chosen values the queue still has. After a language switch a stage or impact area arrives in the
 * new language, so a value chosen in the old one drops out instead of hiding every row.
 */
export function inQueue(filters: Filters, counts: FacetCounts): Filters {
  const has = (key: FacetKey, value: string) => counts[key].some(([v]) => v === value);
  return Object.fromEntries(
    FACET_KEYS.map((key) => [key, filters[key].filter((value) => has(key, value))]),
  ) as Filters;
}
