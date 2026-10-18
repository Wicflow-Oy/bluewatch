import { use, useCallback, useSyncExternalStore } from "react";
import { load } from "../../../data";
import { formatDay } from "../../../lib/format";

/** The breakpoints every screen uses (SCREENS.md §2.1): phone below 720, desktop from 1280. */
export const PHONE = "(max-width: 719px)";
export const BELOW_DESKTOP = "(max-width: 1279px)";

export function useMedia(query: string): boolean {
  const subscribe = useCallback(
    (notify: () => void) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", notify);
      return () => list.removeEventListener("change", notify);
    },
    [query],
  );
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches);
}

/** The app's "today" from /api/meta, so deadlines count down from the same day as the rest of the app. */
export function useToday(): string {
  return use(load.meta()).data.today;
}

const ISO_DAY = /\b\d{4}-\d{2}-\d{2}\b/g;

/** Public records arrive with raw ISO days ("Runs 2023-04-01 to 2027-03-31"); show "1 Apr 2023". */
export function readableDates(text: string, today: string): string {
  return text.replace(ISO_DAY, (iso) => formatDay(iso, { today }));
}
