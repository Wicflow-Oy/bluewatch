// Motion helpers shared by every screen: the row-to-sheet morph (View Transitions API with a CSS fallback),
// reduced-motion checks and CSS custom properties for style props. Spec: TIDEPOOL-SYSTEM.md section 4.
import type { CSSProperties } from "react";
import { flushSync } from "react-dom";

const REDUCED = "(prefers-reduced-motion: reduce)";
let morphing = false;

export function prefersReducedMotion(): boolean {
  return window.matchMedia(REDUCED).matches;
}

/** True while a view transition owns a sheet's enter or exit; ui/Drawer then skips its own animation. */
export function isMorphing(): boolean {
  return morphing;
}

/** CSS custom properties for a style prop: style={vars({ "--i": 3 })}. */
export function vars(values: Record<`--${string}`, string | number>): CSSProperties {
  return values as CSSProperties;
}

type StartViewTransition = (update: () => void) => { finished: Promise<void> };

function onScreen(el: Element): boolean {
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.bottom > 0 && r.top < window.innerHeight;
}

/**
 * Morphs `from` into the element `to()` returns once `update` has rendered. `update` must change the DOM
 * synchronously (use navigateNow, not navigate). Without the API, with reduced motion, in a hidden tab, or when
 * `from` is off screen, it just runs `update`.
 */
export function morph(
  name: string,
  from: Element | null,
  update: () => void,
  to: () => Element | null,
): void {
  const doc = document as Document & { startViewTransition?: StartViewTransition };
  if (
    !doc.startViewTransition ||
    !from ||
    morphing ||
    prefersReducedMotion() ||
    document.visibilityState !== "visible" ||
    !onScreen(from)
  ) {
    update();
    return;
  }
  const source = from as HTMLElement;
  let target: HTMLElement | null = null;
  morphing = true;
  document.documentElement.dataset.vt = name;
  source.style.viewTransitionName = name;
  const transition = doc.startViewTransition.call(document, () => {
    source.style.viewTransitionName = "";
    flushSync(update);
    target = to() as HTMLElement | null;
    if (target) target.style.viewTransitionName = name;
  });
  void transition.finished
    .catch(() => undefined) // a skipped transition still ran the update
    .finally(() => {
      if (target) target.style.viewTransitionName = "";
      delete document.documentElement.dataset.vt;
      morphing = false;
    });
}

/** The open card sheet, for morph(). */
export const sheetPanel = (): Element | null => document.querySelector("[data-sheet-panel]");

/** A list row by its data-row-id, for morph(). */
export const listRow = (id: string): Element | null =>
  document.querySelector(`[data-row-id="${CSS.escape(id)}"]`);
