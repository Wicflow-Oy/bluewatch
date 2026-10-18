// The interface language: a tiny external store, so any module (the API client, date formatting) can read
// it and any component can subscribe without a provider.
import { useSyncExternalStore } from "react";

export type Lang = "en" | "fi" | "sv";

export const LANGS: readonly { code: Lang; label: string }[] = [
  { code: "en", label: "English" },
  { code: "fi", label: "Suomi" },
  { code: "sv", label: "Svenska" },
];

const STORAGE_KEY = "bluewatch.lang";

function isLang(value: unknown): value is Lang {
  return LANGS.some((l) => l.code === value);
}

function storedLang(): Lang {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isLang(stored) ? stored : "en";
  } catch {
    return "en"; // storage can be blocked (private windows); the default is fine
  }
}

let lang: Lang = storedLang();
document.documentElement.lang = lang;
const listeners = new Set<() => void>();

function subscribe(notify: () => void) {
  listeners.add(notify);
  return () => listeners.delete(notify);
}

export function getLang(): Lang {
  return lang;
}

export function setLang(next: Lang): void {
  if (next === lang) return;
  lang = next;
  document.documentElement.lang = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Remembering the language is a convenience only.
  }
  listeners.forEach((notify) => notify());
}

export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getLang);
}

/** An API path with a language (the current one by default), so the server answers in it. */
export function withLang(path: string, language: Lang = lang): string {
  return `${path}${path.includes("?") ? "&" : "?"}lang=${language}`;
}
