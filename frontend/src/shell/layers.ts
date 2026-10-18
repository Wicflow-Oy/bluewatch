// The shell's overlays (search and alerts) are open one at a time, and more than one control opens
// each of them (search opens alerts). A tiny store keeps that in one place instead of threading
// open/close props through every screen.
import { useSyncExternalStore } from "react";

export type Layer = "palette" | "alerts";

let current: Layer | null = null;
const listeners = new Set<() => void>();

function notifyAll(): void {
  listeners.forEach((notify) => notify());
}

export function openLayer(layer: Layer): void {
  if (current === layer) return;
  current = layer;
  notifyAll();
}

/** Closes the layer only if it is still the open one, so a late close never hides a newer layer. */
export function closeLayer(layer: Layer): void {
  if (current !== layer) return;
  current = null;
  notifyAll();
}

function subscribe(notify: () => void) {
  listeners.add(notify);
  return () => listeners.delete(notify);
}

export function useLayer(): Layer | null {
  return useSyncExternalStore(subscribe, () => current);
}
