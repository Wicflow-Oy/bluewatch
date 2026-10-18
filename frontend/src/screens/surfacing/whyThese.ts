import { humanText } from "../../lib/format";

// The API opens with "Why these 10: …" (in the reader's language), which repeats the row label beside it.
const LEAD = /^[^:\d]{1,30}\d+:\s*/;

/** The API's why_these without its "Why these N:" lead, starting with a capital. */
export function whyTheseText(text: string): string {
  const rest = humanText(text.replace(LEAD, ""));
  return rest.charAt(0).toUpperCase() + rest.slice(1);
}
