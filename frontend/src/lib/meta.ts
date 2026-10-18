import { use, useMemo } from "react";
import type { Mode } from "../api";
import { load } from "../data";
import { useWorkspace } from "./workspace";

/** Labels and the demo's "today", worded for the current workspace. */
export function useMeta() {
  const { mode } = useWorkspace();
  const meta = use(load.meta()).data;
  return useMemo(
    () => ({
      mode,
      today: meta.today,
      listName: meta.list_name,
      productName: meta.product_name,
      groupRule: meta.group_rule,
      group: (key: string) => meta.group_labels[key] ?? key,
      /** In the current workspace's words unless another workspace is named. */
      tier: (key: string, inMode: Mode = mode) => meta.tier_labels[inMode]?.[key] ?? key,
      level: (key: string) => meta.level_labels[mode]?.[key] ?? key,
      dimension: (key: string) => meta.dimension_labels[key] ?? key,
    }),
    [meta, mode],
  );
}
