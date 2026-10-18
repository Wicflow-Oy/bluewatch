// The ranking preset: "blue" (the challenge) or the beyond-blue preset that re-ranks the same companies.
// A tiny external store, so any screen can read or switch it without a provider.
import { useEffect, useSyncExternalStore } from "react";
import { load } from "../data";
import { useLang, type Lang } from "../i18n/lang";
import { translator } from "../i18n/messages";
import { presetMessages } from "./messages";

export type PresetName = "blue" | "climate_circular";

export interface PresetOption {
  name: PresetName;
  label: string;
  description: string;
}

const STORAGE_KEY = "bluewatch.preset";
const NAMES: PresetName[] = ["blue", "climate_circular"];

/** Short names for tight places: the segmented control, the breadcrumb chip and search actions. */
export function presetShort(name: PresetName): string {
  return translator(presetMessages).t(`short_${name}`);
}

/** The narrowest form, for the top bar between tablet and desktop widths. */
export function presetAbbr(name: PresetName): string {
  return translator(presetMessages).t(`abbr_${name}`);
}

/** Shown until /api/presets answers in this language, and kept if it never does. */
function builtInOptions(lang: Lang): PresetOption[] {
  const { t } = translator(presetMessages, lang);
  return NAMES.map((name) => ({
    name,
    label: t(`label_${name}`),
    description: t(`description_${name}`),
  }));
}

function isPresetName(value: unknown): value is PresetName {
  return value === "blue" || value === "climate_circular";
}

function storedPreset(): PresetName {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isPresetName(stored) ? stored : "blue";
  } catch {
    return "blue"; // storage can be blocked (private windows); the default is fine
  }
}

interface PresetState {
  preset: PresetName;
  /** The API's wording per language, once it has answered in that language. */
  options: Partial<Record<Lang, PresetOption[]>>;
}

// One immutable snapshot, replaced on every change, so useSyncExternalStore sees label updates too.
let state: PresetState = { preset: storedPreset(), options: {} };
const listeners = new Set<() => void>();
const requested = new Set<Lang>();

function update(next: Partial<PresetState>): void {
  state = { ...state, ...next };
  listeners.forEach((notify) => notify());
}

/** Swaps in the API's wording once per language; a failed request keeps the built-in wording. */
function requestOptions(lang: Lang): void {
  if (requested.has(lang)) return;
  requested.add(lang);
  load.presets().then(
    ({ data }) => {
      const options = builtInOptions(lang).map((fallback) => {
        const info = data.find((p) => p.name === fallback.name);
        return info ? { ...fallback, label: info.label, description: info.description } : fallback;
      });
      update({ options: { ...state.options, [lang]: options } });
    },
    () => undefined,
  );
}

function subscribe(notify: () => void) {
  listeners.add(notify);
  return () => listeners.delete(notify);
}

function getState(): PresetState {
  return state;
}

export function getPreset(): PresetName {
  return state.preset;
}

export function setPreset(next: PresetName): void {
  if (next === state.preset) return;
  update({ preset: next });
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Remembering the preset is a convenience only.
  }
}

/** The current preset, its label, the options for a switch, and the setter. */
export function usePreset(): {
  preset: PresetName;
  setPreset: (next: PresetName) => void;
  label: string;
  options: PresetOption[];
} {
  const { preset, options: byLang } = useSyncExternalStore(subscribe, getState);
  const lang = useLang();
  useEffect(() => requestOptions(lang), [lang]);
  const options = byLang[lang] ?? builtInOptions(lang);
  const label = options.find((o) => o.name === preset)?.label ?? preset;
  return { preset, setPreset, label, options };
}
