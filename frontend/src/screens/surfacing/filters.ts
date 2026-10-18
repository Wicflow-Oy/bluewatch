// The toolbar's filters: one group (or all) and any number of signal chips (OR). Local state, not in the URL.
import type { ListEntry } from "../../contracts";
import { inDisplayOrder, type SurfacingGroup } from "./groups";

export type GroupFilter = "all" | SurfacingGroup;
export type Signal = ListEntry["chip"];

export const SIGNALS: Signal[] = ["newly_founded", "newly_active", "new_to_list"];

export interface Filters {
  group: GroupFilter;
  signals: ReadonlySet<Signal>;
}

export const NO_FILTERS: Filters = { group: "all", signals: new Set() };

/** The rows the filters let through, in display order. */
export function visibleEntries(entries: ListEntry[], f: Filters): ListEntry[] {
  return inDisplayOrder(entries).filter(
    (e) =>
      (f.group === "all" || e.group === f.group) && (f.signals.size === 0 || f.signals.has(e.chip)),
  );
}
