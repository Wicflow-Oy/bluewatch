import { useSyncExternalStore } from "react";

// Matches the phone breakpoint in the CSS (max-width: 719px).
const PHONE = "(max-width: 719px)";

function subscribe(notify: () => void) {
  const query = window.matchMedia(PHONE);
  query.addEventListener("change", notify);
  return () => query.removeEventListener("change", notify);
}

/** True below 720 px, where popovers become sheets. */
export function useIsPhone(): boolean {
  return useSyncExternalStore(subscribe, () => window.matchMedia(PHONE).matches);
}
