// Which scout teams Idea Harbour's queue holds as public leads: queue items are "hackathon:{project id}".
// Read once per workspace and preset; null when the queue can't be read, so the scout still works.
import type { Mode } from "../../api";
import type { PresetName } from "../../lib/preset";
import { ideasApi } from "../ideas/api";

const queued = new Map<string, Promise<Set<string> | null>>();

export const queueItemId = (projectId: string) => `hackathon:${projectId}`;

export function queuedIdeas(mode: Mode, preset: PresetName): Promise<Set<string> | null> {
  const key = `${mode}:${preset}`;
  let hit = queued.get(key);
  if (!hit) {
    hit = ideasApi.queue(mode, preset).then(
      (queue) => new Set(queue.items.map((item) => item.id)),
      () => null,
    );
    queued.set(key, hit);
  }
  return hit;
}
