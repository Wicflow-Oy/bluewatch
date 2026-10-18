// Desk keys as words. The server sends keys (a route, a ledger field, a language code); a key the
// screen has no words for is still shown, made readable, rather than hidden.
import type { OutreachDraft } from "../../contracts";
import { humanText, ofN } from "../../lib/format";
import type { OutreachT, OutreachText } from "./messages";

const ROUTES = ["org_generic", "role_authorised", "consent"] as const;
const GAP_FIELDS = [
  "customers",
  "product",
  "team",
  "funding",
  "business_model",
  "market",
  "impact",
  "tech",
  "trl",
  "public_contracts",
  "partners",
  "pilot",
] as const;
const DRAFT_LANGUAGES = ["en", "fi", "sv", "no", "et"] as const;
const DRAFT_MODES = ["evidence_request", "first_touch"] as const;

type Lawful = (typeof ROUTES)[number];
type GapField = (typeof GAP_FIELDS)[number];
type DraftLanguageCode = NonNullable<OutreachDraft["language"]>;
type DraftMode = (typeof DRAFT_MODES)[number];

const isOneOf = <T extends string>(list: readonly T[], value: string): value is T =>
  (list as readonly string[]).includes(value);

/** "General company address" for "org_generic". */
export function routeLabel(t: OutreachT, route: string): string {
  return isOneOf<Lawful>(ROUTES, route) ? t(`route_${route}`) : humanText(route);
}

/** "Customers" for the ledger field "customers". */
export function gapLabel(t: OutreachT, field: string): string {
  return isOneOf<GapField>(GAP_FIELDS, field) ? t(`gap_${field}`) : humanText(field);
}

/** "Finnish" for "fi", in the interface language. */
export function languageLabel(t: OutreachT, code: string): string {
  return isOneOf<DraftLanguageCode>(DRAFT_LANGUAGES, code) ? t(`language_${code}`) : code;
}

/** "Evidence request" for "evidence_request". */
export function modeLabel(t: OutreachT, mode: string): string {
  return isOneOf<DraftMode>(DRAFT_MODES, mode) ? t(`mode_${mode}`) : humanText(mode);
}

/** "Answered 2 of 2 questions". */
export function answeredWords(k: number, n: number, { tn }: OutreachText): string {
  return tn("answered", n, { count: ofN(k, n) });
}
