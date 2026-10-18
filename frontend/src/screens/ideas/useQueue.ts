import { useCallback, useEffect, useState } from "react";
import type { Mode } from "../../api";
import { ideasQueue } from "../../data";
import { useLang } from "../../i18n/lang";
import type { PresetName } from "../../lib/preset";
import type { IdeaQueue } from "./types";

/** The live queue, or the sample-data preview filled with invented ideas. */
export type QueueSource = "live" | "sample";

interface Loaded {
  key: string;
  source: QueueSource;
  queue: IdeaQueue | null;
  failed: boolean;
}

async function fetchQueue(
  source: QueueSource,
  mode: Mode,
  preset: PresetName,
  topN: number,
): Promise<IdeaQueue> {
  const sample = source === "sample";
  const queue = await ideasQueue(mode, preset, topN, sample);
  // A server that ignores the sample parameter sends the live queue: never show it under the banner.
  if (queue.sample !== sample) throw new Error(`The server sent no ${source} queue.`);
  return queue;
}

/**
 * A'Pelago's review queue for the source, workspace, preset, Top N and language. It refetches when the
 * window regains focus, so an idea shared from the student form appears without a reload.
 */
export function useQueue(source: QueueSource, mode: Mode, preset: PresetName, topN: number) {
  const lang = useLang();
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState<Loaded>({
    key: "",
    source,
    queue: null,
    failed: false,
  });
  const key = `${source}/${mode}/${preset}/${topN}/${lang}/${attempt}`;

  useEffect(() => {
    let current = true;
    fetchQueue(source, mode, preset, topN).then(
      (queue) => current && setLoaded({ key, source, queue, failed: false }),
      () => current && setLoaded((last) => ({ ...last, key, failed: true })),
    );
    return () => {
      current = false;
    };
  }, [key, source, mode, preset, topN]);

  const refetch = useCallback(() => setAttempt((n) => n + 1), []);

  useEffect(() => {
    window.addEventListener("focus", refetch);
    return () => window.removeEventListener("focus", refetch);
  }, [refetch]);

  // A queue for another source, workspace, preset or Top N is never shown, not even while the next
  // one loads: sample ideas must never appear under the live queue, nor live ones under the banner.
  const last = loaded.queue;
  const queue =
    last &&
    loaded.source === source &&
    last.mode === mode &&
    last.preset === preset &&
    last.top_n === topN
      ? last
      : null;
  return { queue, failed: queue === null && loaded.key === key && loaded.failed, retry: refetch };
}
