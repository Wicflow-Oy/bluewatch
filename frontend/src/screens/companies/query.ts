// What a visitor typed into "Look up any company": a business ID (looked up directly) or a name
// (searched in the registers). The text stays in memory; it never goes into the URL or storage.
import type { Country } from "../../api";

export type LookupCountry = Country | "any";

/** Why typed text can't be looked up; the panel words it in the interface language. */
export type QueryProblem = "checkDigit" | "formatAny" | `format_${Country}` | "tooShort";

export type ParsedQuery =
  | { kind: "id"; country: Country; businessId: string }
  | { kind: "name"; name: string }
  | { kind: "invalid"; problem: QueryProblem };

export const MIN_NAME_LENGTH = 3;
const COUNTRIES: Country[] = ["FI", "NO", "EE"];

const ID_FORMATS: Record<Country, RegExp> = {
  FI: /^\d{7}-?\d$/,
  NO: /^\d{9}$/,
  EE: /^\d{8}$/,
};

/** Without a country, the format decides; 8 digits read as Estonian, since Finnish IDs carry a dash. */
function countryOf(compact: string): Country | null {
  if (/^\d{7}-\d$/.test(compact)) return "FI";
  if (ID_FORMATS.NO.test(compact)) return "NO";
  if (ID_FORMATS.EE.test(compact)) return "EE";
  return null;
}

const CHECK_WEIGHTS: Partial<Record<Country, number[]>> = {
  FI: [7, 9, 10, 5, 8, 4, 2],
  NO: [3, 2, 7, 6, 5, 4, 3, 2],
};

/** The modulus-11 check digit of a Finnish or Norwegian ID, so a typo is caught before any request. */
function checkDigitMatches(country: Country, id: string): boolean {
  const weights = CHECK_WEIGHTS[country];
  if (!weights) return true; // Estonian codes are checked by the register
  const digits = id.replace("-", "").split("").map(Number);
  const sum = weights.reduce((total, w, i) => total + w * digits[i], 0);
  const remainder = sum % 11;
  const expected = remainder === 0 ? 0 : 11 - remainder;
  return expected !== 10 && expected === digits[weights.length];
}

export function parseQuery(raw: string, country: LookupCountry): ParsedQuery {
  const text = raw.trim().replace(/\s+/g, " ");
  const squeezed = text.replace(/[\s.]/g, "");
  // "FI31017913" and "NO 938 525 420" carry their country in front.
  const prefix = /^(FI|NO|EE)(?=\d)/i.exec(squeezed)?.[1].toUpperCase();
  const typedCountry = COUNTRIES.find((c) => c === prefix) ?? null;
  const compact = typedCountry ? squeezed.slice(2) : squeezed;
  if (/^[\d-]+$/.test(compact)) {
    const idCountry = country === "any" ? (typedCountry ?? countryOf(compact)) : country;
    if (idCountry && ID_FORMATS[idCountry].test(compact))
      return checkDigitMatches(idCountry, compact)
        ? { kind: "id", country: idCountry, businessId: compact }
        : { kind: "invalid", problem: "checkDigit" };
    return { kind: "invalid", problem: country === "any" ? "formatAny" : `format_${country}` };
  }
  if (text.length < MIN_NAME_LENGTH) return { kind: "invalid", problem: "tooShort" };
  return { kind: "name", name: text };
}
