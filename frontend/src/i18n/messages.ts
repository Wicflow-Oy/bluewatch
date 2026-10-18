// Interface text lives next to the feature that shows it, in one messages.ts per feature:
//
//   export const messages = defineMessages({ en: { hello: "Hello {name}" }, fi: {...}, sv: {...} });
//   const { t } = useT(messages);  t("hello", { name })
//
// fi and sv must have exactly en's keys, so a missing or stray translation fails the type check.
import { useMemo } from "react";
import { getLang, useLang, type Lang } from "./lang";

type Catalogue = Record<string, string>;

export interface Messages<K extends string> {
  en: Record<K, string>;
  fi: Record<K, string>;
  sv: Record<K, string>;
}

export function defineMessages<const E extends Catalogue>(messages: {
  en: E;
  fi: { [K in keyof E]: string };
  sv: { [K in keyof E]: string };
}): Messages<Extract<keyof E, string>> {
  return messages;
}

export type Params = Record<string, string | number>;

/** "count" for keys "count_one" and "count_other": the bases tn() can pick a plural form of. */
type PluralBase<K extends string> = K extends `${infer Base}_other` ? Base : never;

export interface Translator<K extends string> {
  /** The message in the current language with {param} placeholders filled in. */
  t: (key: K, params?: Params) => string;
  /** The plural form of `base` for n (keys base_one and base_other); n is available as {n}. */
  tn: (base: PluralBase<K>, n: number, params?: Params) => string;
}

const LOCALES: Record<Lang, string> = { en: "en-GB", fi: "fi-FI", sv: "sv-SE" };

/** The Intl locale for a language: British English, Finnish, Swedish. */
export function localeOf(lang: Lang = getLang()): string {
  return LOCALES[lang];
}

/** The language's decimal sign and digit grouping, never rounding; a year such as 2026 stays ungrouped. */
function formatNumber(value: number, lang: Lang): string {
  return new Intl.NumberFormat(LOCALES[lang], {
    maximumFractionDigits: 20,
    useGrouping: Math.abs(value) >= 10_000,
  }).format(value);
}

function fill(text: string, params: Params | undefined, lang: Lang): string {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (whole, name: string) => {
    const value = params[name];
    if (value === undefined) return whole;
    return typeof value === "number" ? formatNumber(value, lang) : value;
  });
}

/** For code outside components (labels, page titles); components use useT so they re-render on a switch. */
export function translator<K extends string>(
  messages: Messages<K>,
  lang: Lang = getLang(),
): Translator<K> {
  const catalogue = messages[lang];
  const plural = new Intl.PluralRules(LOCALES[lang]);
  const t = (key: K, params?: Params) => fill(catalogue[key], params, lang);
  const tn = (base: PluralBase<K>, n: number, params?: Params) => {
    const form = `${base}_${plural.select(n)}`;
    const key = (form in catalogue ? form : `${base}_other`) as K;
    return t(key, { n, ...params });
  };
  return { t, tn };
}

export function useT<K extends string>(messages: Messages<K>): Translator<K> {
  const lang = useLang();
  return useMemo(() => translator(messages, lang), [messages, lang]);
}
