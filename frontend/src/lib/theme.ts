// The colour theme: Light (default) or Graphite, on <html data-theme>. public/theme-init.js applies the stored
// choice before first paint; this store keeps it in sync afterwards. The OS colour scheme is not followed.
import { useSyncExternalStore } from "react";

export type Theme = "light" | "graphite";

const KEY = "bluewatch.theme";
const META: Record<Theme, string> = { light: "#F4F4F1", graphite: "#0F1012" };

let theme: Theme = document.documentElement.dataset.theme === "graphite" ? "graphite" : "light";
const listeners = new Set<() => void>();

function subscribe(notify: () => void) {
  listeners.add(notify);
  return () => listeners.delete(notify);
}

export function getTheme(): Theme {
  return theme;
}

export function setTheme(next: Theme): void {
  if (next === theme) return;
  theme = next;
  if (next === "graphite") document.documentElement.dataset.theme = "graphite";
  else delete document.documentElement.dataset.theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", META[next]);
  try {
    window.localStorage.setItem(KEY, next);
  } catch {
    // Remembering the theme is a convenience only.
  }
  listeners.forEach((notify) => notify());
}

export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, getTheme);
}
