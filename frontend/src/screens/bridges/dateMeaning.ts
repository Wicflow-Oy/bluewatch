import type { Bridge } from "../../contracts";

/** What a bridge's date is: a call or tender closing, a research project ending, or a law starting to apply. */
export type DateMeaning = "deadline" | "projectEnds" | "appliesFrom";

export function dateMeaning(bridge: Bridge): DateMeaning {
  if (bridge.type === "law_creates_buyer") return "appliesFrom";
  const evidence = [...bridge.evidence_company, ...bridge.evidence_counterparty];
  const isDeadline = evidence.some((e) => e.deadline === bridge.deadline);
  const isProjectEnd = evidence.some((e) => e.end === bridge.deadline);
  return isProjectEnd && !isDeadline ? "projectEnds" : "deadline";
}
