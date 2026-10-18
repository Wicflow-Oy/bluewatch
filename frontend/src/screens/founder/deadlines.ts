// Deadline order and windows shared by the tiers, the comparison strip and the next 30 days.
import { daysUntil } from "../../lib/format";

interface Dated {
  deadline?: string | null;
}

/** Soonest deadline first; items without a published deadline after them, in their given order. */
export function soonestFirst(a: Dated, b: Dated): number {
  if (!a.deadline || !b.deadline) return Number(!a.deadline) - Number(!b.deadline);
  return a.deadline.localeCompare(b.deadline);
}

/** Items due within `days` of `today`, and items with no deadline; closed and later ones are left out. */
export function splitByWindow<T extends Dated>(
  items: T[],
  today: string,
  days: number,
): { dated: T[]; undated: T[] } {
  const within = (item: T) => {
    const left = item.deadline ? daysUntil(item.deadline, today) : null;
    return left !== null && left >= 0 && left <= days;
  };
  return { dated: items.filter(within), undated: items.filter((item) => !item.deadline) };
}
