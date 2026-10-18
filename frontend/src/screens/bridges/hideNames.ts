// "Hide names": a privacy switch for sharing a screen. While it is on, the company side of every bridge
// shows a description from register data instead of the name, and its register ID and links are hidden.
// Words that would name it anyway (a project acronym, its organisation, a product) read "[hidden]".
// Remembered for this tab only.
import { useCallback, useState } from "react";
import type { Bridge } from "../../contracts";
import { translator } from "../../i18n/messages";
import { bridgesMessages } from "./messages";

const STORAGE_KEY = "bluewatch.hide-names";

function stored(): boolean {
  try {
    return window.sessionStorage.getItem(STORAGE_KEY) === "on";
  } catch {
    return false; // storage can be blocked (private windows); off is the safe default
  }
}

export function useHideNames(): [boolean, (on: boolean) => void] {
  const [on, setOn] = useState(stored);
  const set = useCallback((next: boolean) => {
    setOn(next);
    try {
      window.sessionStorage.setItem(STORAGE_KEY, next ? "on" : "off");
    } catch {
      // Remembering the switch is a convenience only.
    }
  }, []);
  return [on, set];
}

/** What stands in for a company's name while names are hidden; the API sends a description from register data. */
export function hiddenName(bridge: Bridge): string {
  return bridge.anonymised_name ?? translator(bridgesMessages).t("aCompany");
}

/** Who stands in for the open bridge's company; null when names are shown. */
export interface Alias {
  bridge: Bridge;
  name: string;
  /** The other words that name the company (a project acronym, an organisation, a product). */
  terms: RegExp | null;
}

const escaped = (term: string) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Each term at the start of a word, in any case: "Groke" also finds "Groke PRO", "Datadeck" finds "DataDeck". */
function termsPattern(terms: string[]): RegExp | null {
  const longestFirst = [...terms].filter(Boolean).sort((a, b) => b.length - a.length);
  if (longestFirst.length === 0) return null;
  return new RegExp(`(?<![\\p{L}\\p{N}])(?:${longestFirst.map(escaped).join("|")})`, "giu");
}

export function aliasFor(hero: Bridge, hide: boolean): Alias | null {
  if (!hide) return null;
  return {
    bridge: hero,
    name: hiddenName(hero),
    terms: termsPattern(hero.identifying_terms ?? []),
  };
}

/** Nothing that names the company shows while hidden, including inside sentences from the API. */
export function hideName(text: string, alias: Alias | null): string {
  if (!alias) return text;
  const hidden = translator(bridgesMessages).t("hiddenTerm");
  return text
    .split(alias.bridge.company.name)
    .map((part) => (alias.terms ? part.replace(alias.terms, hidden) : part))
    .join(alias.name);
}
