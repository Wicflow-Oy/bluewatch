// What a failed request means for the visitor (IDEA-HARBOUR.md §3.8). Every case says what still works.
import { ApiError } from "../../api";
import { fieldError, type TextField } from "./draft";
import { own, type Message } from "./message";

export interface Banner {
  tone: "error" | "warn";
  message: Message;
}

export type Outcome =
  | { kind: "field"; field: TextField | "links"; message: Message }
  | { kind: "banner"; banner: Banner };

const banner = (tone: Banner["tone"], message: Message): Outcome => ({
  kind: "banner",
  banner: { tone, message },
});

export function explain(error: unknown): Outcome {
  // Anything else is a bug in this page, not a server answer: let it surface.
  if (!(error instanceof ApiError)) throw error;
  const field = fieldError(error);
  if (field) return { kind: "field", field: field.field, message: { text: field.text } };
  switch (error.status) {
    case 0:
      return banner("error", own("unreachable"));
    case 413:
      return banner("error", own("tooLong"));
    case 429:
      return banner("warn", error.detail ? { text: error.detail } : own("rateLimited"));
    case 409:
      return banner("error", own("consentChanged"));
    default:
      return banner(
        "error",
        error.status === 422 && error.detail ? { text: error.detail } : own("serverFailed"),
      );
  }
}

/** One message for places that show a single line (the share panel). */
export function outcomeMessage(outcome: Outcome): Message {
  return outcome.kind === "field" ? outcome.message : outcome.banner.message;
}
