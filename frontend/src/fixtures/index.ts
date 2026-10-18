// The demo pack: snapshots of the real API output, written by scripts/snapshot_fixtures.py (do not edit
// the JSON by hand). Each file is its own lazy chunk, so the app downloads one only when the API is down.

interface Snapshot {
  generated_by: string;
  generated_at: string;
  data: unknown;
}

const SNAPSHOTS = import.meta.glob<Snapshot>("./*.json", { import: "default" });

/** The snapshot's data, or null when no snapshot was recorded under that name. */
export async function snapshot<T>(name: string): Promise<T | null> {
  const loadFile = SNAPSHOTS[`./${name}.json`];
  // The cast is safe by construction: the script wrote this file from the same typed API route.
  return loadFile ? ((await loadFile()).data as T) : null;
}

/** For snapshots the script always writes (meta, lists, ...): a missing one is a build bug. */
export async function requiredSnapshot<T>(name: string): Promise<T> {
  const data = await snapshot<T>(name);
  if (data === null)
    throw new Error(`Missing demo snapshot ${name}.json: run scripts/snapshot_fixtures.py`);
  return data;
}
