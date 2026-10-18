import type { ListEntry } from "../../contracts";
import { GROUP_ORDER, type Group } from "../../lib/labels";

/** The groups the list shows; "not for us" never surfaces. */
export type SurfacingGroup = Exclude<Group, "not_for_us">;

export const SURFACING_GROUPS = GROUP_ORDER.filter((g): g is SurfacingGroup => g !== "not_for_us");

/** Rows in the order they are shown: by group, then by rank within the group. */
export function inDisplayOrder(entries: ListEntry[]): ListEntry[] {
  return SURFACING_GROUPS.flatMap((g) => entries.filter((e) => e.group === g));
}
