// Keyboard movement through the visible rows: J/K anywhere on the page, arrow keys while focus is in the list,
// R to start the review at the first row. Moving focuses the row's name link, so Enter opens it like a click.
import { useEffect } from "react";

const NEXT = new Set(["j", "ArrowDown"]);
const PREVIOUS = new Set(["k", "ArrowUp"]);
const START = "r";

function isTyping(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

/** Focuses a row's name link and scrolls the row into view. */
export function focusRow(companyId: string) {
  const link = document.querySelector<HTMLElement>(
    `[data-row-id="${CSS.escape(companyId)}"] .srow__name`,
  );
  link?.focus({ preventScroll: true });
  link?.closest("[data-row-id]")?.scrollIntoView({ block: "nearest" });
}

export function useListKeys(
  /** The visible rows' ids in display order. */
  ids: string[],
  currentId: string | undefined,
  onMove: (companyId: string) => void,
  paused: boolean,
) {
  useEffect(() => {
    if (paused) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return;
      const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
      const step = NEXT.has(key) ? 1 : PREVIOUS.has(key) ? -1 : 0;
      if (step === 0 && key !== START) return;
      const inList = e.target instanceof Element && e.target.closest(".shortlist") !== null;
      if (key.startsWith("Arrow") && !inList) return;

      const at = currentId ? ids.indexOf(currentId) : -1;
      const next =
        key === START
          ? ids[0]
          : ids[at === -1 ? 0 : Math.min(ids.length - 1, Math.max(0, at + step))];
      if (!next) return;
      e.preventDefault();
      onMove(next);
      focusRow(next);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ids, currentId, onMove, paused]);
}
