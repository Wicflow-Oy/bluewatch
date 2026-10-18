// The sliding pill behind the selected item of a segmented control, the nav pills, tabs and the phone tab bar.
import { useCallback, useEffect, useLayoutEffect, useRef } from "react";

const SELECTED =
  ':scope > [data-selected="true"], :scope > [aria-selected="true"], :scope > [aria-current="page"]';

/**
 * Moves an absolutely positioned indicator (<span class="seg__ind">, a child of the root) under the selected child.
 * The first placement and any resize jump without animating; a change of selection slides (--d-slide, --spring-soft).
 * `itemsKey` changes when the set of options changes (for example a language switch renames them).
 */
export function useSlidingIndicator<T extends HTMLElement = HTMLElement>(
  selectedKey: string | null | undefined,
  itemsKey = "",
) {
  const rootRef = useRef<T>(null);
  const indRef = useRef<HTMLSpanElement>(null);
  const placedOnce = useRef(false);

  const place = useCallback((animate: boolean) => {
    const root = rootRef.current;
    const ind = indRef.current;
    if (!root || !ind || root.offsetWidth === 0) return; // hidden (display: none) at this width
    const on = root.querySelector<HTMLElement>(SELECTED);
    if (!on) {
      ind.style.opacity = "0";
      return;
    }
    const jump = !animate || !placedOnce.current;
    if (jump) ind.setAttribute("data-instant", "");
    ind.style.opacity = "1";
    ind.style.width = `${on.offsetWidth}px`;
    ind.style.transform = `translateX(${on.offsetLeft}px)`;
    if (jump) {
      void ind.offsetWidth; // commit the jump before transitions return
      ind.removeAttribute("data-instant");
    }
    placedOnce.current = true;
  }, []);

  useLayoutEffect(() => place(true), [selectedKey, itemsKey, place]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const observer = new ResizeObserver(() => place(false));
    observer.observe(root);
    for (const child of Array.from(root.children)) observer.observe(child);
    void document.fonts?.ready.then(() => place(false));
    return () => observer.disconnect();
  }, [itemsKey, place]);

  return { rootRef, indRef };
}
