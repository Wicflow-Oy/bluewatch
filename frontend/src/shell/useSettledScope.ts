import { useDeferredValue } from "react";
import type { Mode } from "../api";
import { usePreset, type PresetName } from "../lib/preset";
import { useWorkspace } from "../lib/workspace";

/** The workspace and preset for the shell's own data (counts, crumbs, alerts). While a switch loads,
 * React keeps showing the previous values instead of a skeleton, so the chrome never flickers. */
export function useSettledScope(): { mode: Mode; preset: PresetName } {
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  return { mode: useDeferredValue(mode), preset: useDeferredValue(preset) };
}
