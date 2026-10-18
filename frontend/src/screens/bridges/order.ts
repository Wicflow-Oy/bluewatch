import type { Bridge } from "../../contracts";

const CONFIDENCE_RANK: Record<Bridge["confidence"], number> = {
  verified: 0,
  probable: 1,
  possible: 2,
};

/** ISO days compare as text; a bridge without a deadline goes last. */
function compareDeadlines(a: Bridge, b: Bridge): number {
  if (a.deadline === b.deadline) return 0;
  if (!a.deadline) return 1;
  if (!b.deadline) return -1;
  return a.deadline < b.deadline ? -1 : 1;
}

const compareConfidence = (a: Bridge, b: Bridge) =>
  CONFIDENCE_RANK[a.confidence] - CONFIDENCE_RANK[b.confidence];

/** The list order: soonest deadline first, then the surest. */
export function byDeadline(a: Bridge, b: Bridge): number {
  return compareDeadlines(a, b) || compareConfidence(a, b);
}

/** The hero when no bridge is named: the surest first, then the soonest deadline. */
export function byStrength(a: Bridge, b: Bridge): number {
  return compareConfidence(a, b) || compareDeadlines(a, b);
}

/** Verified and probable: the bridges the list opens on. */
export const isStrong = (b: Bridge) => b.confidence !== "possible";
