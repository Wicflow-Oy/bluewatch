// The data layer: the real API first, the demo pack (snapshots of the same API, see fixtures/) when the
// API is not reachable, failing (5xx) or not routed (404). Anything served
// from the demo pack flips the "Demo data" chip in the top bar, so a visitor always knows what they see.
// Where no snapshot can stand in (the outreach desk, an ID nobody recorded), the answer is "unavailable".
import { useSyncExternalStore } from "react";
import {
  api,
  ApiError,
  type CardLookupResponse,
  type CardReadResponse,
  type Country,
  type DraftLanguage,
  type FounderResponse,
  type Meta,
  type Mode,
  type SearchResponse,
  type ShareReceipt,
} from "./api";
import type {
  Alert,
  AuditEvent,
  Bridge,
  CompanyRow,
  ContactPlan,
  DeskDraft,
  DeskReply,
  FundingCatalogue,
  PrecisionReport,
  PresetInfo,
  ShortList,
  SourceStatus,
  VentureCard,
} from "./contracts";
import { requiredSnapshot, snapshot } from "./fixtures";
import { getLang, type Lang } from "./i18n/lang";
import type { PresetName } from "./lib/preset";
import { DEFAULT_TOP_N, ideasApi } from "./screens/ideas/api";
import type { IdeaQueue } from "./screens/ideas/types";

export type Origin = "live" | "demo";

export interface Loaded<T> {
  data: T;
  origin: Origin;
}

/** For actions that can be refused (bad input, rate limit, state machine) or have no fallback at all. */
export type Outcome<T> =
  | { kind: "result"; data: T; origin: Origin }
  | { kind: "rejected"; message: string; status?: number }
  | { kind: "unavailable" };

// ---- the "Demo data" chip

let demoInUse = false;
const listeners = new Set<() => void>();

function demo<T>(data: T): Loaded<T> {
  if (!demoInUse) {
    demoInUse = true;
    listeners.forEach((notify) => notify());
  }
  return { data, origin: "demo" };
}

function subscribe(notify: () => void) {
  listeners.add(notify);
  return () => listeners.delete(notify);
}

export function useDemoInUse(): boolean {
  return useSyncExternalStore(subscribe, () => demoInUse);
}

// ---- loads, memoised per language so screens can call them during render with React's use()

const cache = new Map<string, Promise<unknown>>();

function memo<T>(key: string, run: () => Promise<T>, lang: Lang = getLang()): Promise<T> {
  const langKey = `${lang}:${key}`;
  let hit = cache.get(langKey) as Promise<T> | undefined;
  if (!hit) {
    hit = run();
    cache.set(langKey, hit);
  }
  return hit;
}

/** Not reachable, not built yet, or not routed yet. Anything else (a 422, a bug) is a real error. */
function apiNotReady(err: unknown): boolean {
  return err instanceof ApiError && (err.status === 0 || err.status === 404 || err.status >= 500);
}

/** In a given language, so a language switch can load the new labels before it shows them. */
function loadMeta(lang: Lang = getLang()): Promise<Loaded<Meta>> {
  return memo(
    "meta",
    () =>
      api.meta(lang).then(
        (data): Loaded<Meta> => ({ data, origin: "live" }),
        async (err: unknown) => {
          if (!apiNotReady(err)) throw err;
          return demo(await requiredSnapshot<Meta>("meta"));
        },
      ),
    lang,
  );
}

/** Once /api/meta has failed, the session stays on the demo pack instead of firing doomed requests. */
async function liveOrDemo<T>(
  live: () => Promise<T>,
  fallback: () => Promise<T>,
): Promise<Loaded<T>> {
  const meta = await loadMeta();
  if (meta.origin === "demo") return demo(await fallback());
  try {
    return { data: await live(), origin: "live" };
  } catch (err) {
    if (!apiNotReady(err)) throw err;
    return demo(await fallback());
  }
}

/** Same, for answers that only exist live or in the demo pack: null when neither has one. */
async function liveOrRecorded<T>(
  live: () => Promise<T>,
  recorded: () => Promise<T | null>,
): Promise<Loaded<T> | null> {
  const meta = await loadMeta();
  if (meta.origin === "live") {
    try {
      return { data: await live(), origin: "live" };
    } catch (err) {
      if (!apiNotReady(err)) throw err;
    }
  }
  const data = await recorded();
  return data === null ? null : demo(data);
}

const settled = new WeakMap<Promise<unknown>, Promise<unknown>>();

/** For optional extras (search groups, the alerts bell): the data, or null when the load failed.
 * Memoised per load, so screens can read it during render with use(). */
export function dataOrNull<T>(loading: Promise<Loaded<T>>): Promise<T | null> {
  let hit = settled.get(loading) as Promise<T | null> | undefined;
  if (!hit) {
    hit = loading.then(
      (loaded) => loaded.data,
      () => null,
    );
    settled.set(loading, hit);
  }
  return hit;
}

const cardsOf = (mode: Mode, preset: PresetName) =>
  snapshot<Record<string, VentureCard>>(`cards.${mode}.${preset}`);

export const load = {
  meta: loadMeta,
  // The demo pack has no sources snapshot of its own; the recorded list carries the same statuses.
  sources: (): Promise<Loaded<SourceStatus[]>> =>
    memo("sources", () =>
      liveOrDemo(api.sources, async () => {
        const list = await requiredSnapshot<ShortList>("list.apelago.blue");
        return list.sources ?? [];
      }),
    ),
  presets: (): Promise<Loaded<PresetInfo[]>> =>
    memo("presets", () => liveOrDemo(api.presets, () => requiredSnapshot("presets"))),
  list: (mode: Mode, preset: PresetName = "blue"): Promise<Loaded<ShortList>> =>
    memo(`list:${mode}:${preset}`, () =>
      liveOrDemo(
        () => api.list(mode, preset),
        () => requiredSnapshot(`list.${mode}.${preset}`),
      ),
    ),
  companies: (mode: Mode, preset: PresetName = "blue"): Promise<Loaded<CompanyRow[]>> =>
    memo(`companies:${mode}:${preset}`, () =>
      liveOrDemo(
        () => api.companies(mode, preset),
        () => requiredSnapshot(`companies.${mode}.${preset}`),
      ),
    ),
  /** null: no card for this company, live or in the demo pack (only listed companies are recorded). */
  card: (
    companyId: string,
    mode: Mode,
    preset: PresetName = "blue",
  ): Promise<Loaded<VentureCard> | null> =>
    memo(`card:${mode}:${preset}:${companyId}`, () =>
      liveOrRecorded(
        () => api.card(companyId, mode, preset),
        async () => (await cardsOf(mode, preset))?.[companyId] ?? null,
      ),
    ),
  bridges: (mode: Mode): Promise<Loaded<Bridge[]>> =>
    memo(`bridges:${mode}`, () =>
      liveOrDemo(
        () => api.bridges(mode),
        () => requiredSnapshot(`bridges.${mode}`),
      ),
    ),
  /** null: no live bridge with this id in this workspace. */
  bridge: (bridgeId: string, mode: Mode): Promise<Loaded<Bridge> | null> =>
    memo(`bridge:${mode}:${bridgeId}`, async () => {
      const all = await load.bridges(mode);
      const found = all.data.find((b) => b.id === bridgeId);
      return found ? { data: found, origin: all.origin } : null;
    }),
  funding: (mode: Mode): Promise<Loaded<FundingCatalogue>> =>
    memo(`funding:${mode}`, () =>
      liveOrDemo(
        () => api.funding(mode),
        () => requiredSnapshot(`funding.${mode}`),
      ),
    ),
  alerts: (mode: Mode): Promise<Loaded<Alert[]>> =>
    memo(`alerts:${mode}`, () =>
      liveOrDemo(
        () => api.alerts(mode),
        () => requiredSnapshot(`alerts.${mode}`),
      ),
    ),
  precision: (): Promise<Loaded<PrecisionReport>> =>
    memo("precision", () => liveOrDemo(api.precision, () => requiredSnapshot("precision"))),
  scout: (mode: Mode): Promise<Loaded<ContactPlan[]>> =>
    memo(`scout:${mode}`, () =>
      liveOrDemo(
        () => api.scout(mode),
        () => requiredSnapshot(`scout.${mode}`),
      ),
    ),
};

// ---- actions with visitor input: never cached and never stored (the input stays in memory only, and
// only while its request runs)

const FORMAT_HINT: Record<Country, string> = {
  FI: "A Finnish business ID looks like 1234567-8.",
  NO: "A Norwegian organisation number has 9 digits.",
  EE: "An Estonian registry code has 8 digits.",
};

const compactId = (businessId: string) => businessId.replace(/[\s.]/g, "");

const inFlight = new Map<string, Promise<unknown>>();

/** One request per question and language at a time: a repeat click shares the answer already on its
 * way. Nothing is kept once it settles. */
function shared<T>(key: string, run: () => Promise<T>): Promise<T> {
  const langKey = `${getLang()}:${key}`;
  const hit = inFlight.get(langKey) as Promise<T> | undefined;
  if (hit) return hit;
  const started = run().finally(() => inFlight.delete(langKey));
  inFlight.set(langKey, started);
  return started;
}

/** Idea Harbour's review queue, live only. The sidebar count and #/ideas ask for it at the same moments
 * (opening the page, the window regaining focus), so one request answers both; it is read again on the
 * next ask, so an idea shared from another tab shows up. */
export function ideasQueue(
  mode: Mode,
  preset: PresetName,
  topN = DEFAULT_TOP_N,
  sample = false,
): Promise<IdeaQueue> {
  return shared(`ideas:${mode}:${preset}:${topN}:${sample ? "sample" : "live"}`, () =>
    ideasApi.queue(mode, preset, topN, { sample }),
  );
}

/** Live first; on a refusal the API's own words; else the recording for a demo ID, or unavailable. */
async function attempt<T>(
  live: () => Promise<T>,
  recorded: () => Promise<T | null>,
  refusedHint: string,
): Promise<Outcome<T>> {
  const meta = await loadMeta();
  if (meta.origin === "live") {
    try {
      return { kind: "result", data: await live(), origin: "live" };
    } catch (err) {
      if (err instanceof ApiError && [409, 413, 422, 429].includes(err.status)) {
        return { kind: "rejected", message: err.detail ?? refusedHint, status: err.status };
      }
      if (!apiNotReady(err)) throw err;
    }
  }
  const data = await recorded();
  // demo() flips the top bar's "Demo data" chip: a recorded answer must never pass as live.
  return data === null ? { kind: "unavailable" } : { kind: "result", ...demo(data) };
}

const asked = new WeakMap<object, Map<string, Promise<unknown>>>();

/** The answer to one question a screen asked (`question` is the state object that holds it), per
 * language, workspace or whatever else `key` names. React may render a screen several times before it
 * shows it, so a request started during render must come from here to be sent once. Forgotten with the
 * question. */
export function askOnce<T>(question: object, key: string, ask: () => Promise<T>): Promise<T> {
  let answers = asked.get(question);
  if (!answers) {
    answers = new Map();
    asked.set(question, answers);
  }
  let answer = answers.get(key) as Promise<T> | undefined;
  if (!answer) {
    answer = ask();
    answers.set(key, answer);
  }
  return answer;
}

export function lookupFounder(
  country: Country,
  businessId: string,
): Promise<Outcome<FounderResponse>> {
  return shared(`founder:${country}:${compactId(businessId)}`, () =>
    attempt(
      () => api.founder(country, businessId),
      async () =>
        (await snapshot<Record<string, FounderResponse>>("founder"))?.[
          `${country}:${compactId(businessId)}`
        ] ?? null,
      FORMAT_HINT[country],
    ),
  );
}

/** Any business ID as a venture card. Offline, only the listed companies' recorded cards stand in. */
export function lookupCard(
  country: Country,
  businessId: string,
  mode: Mode,
  preset: PresetName = "blue",
): Promise<Outcome<CardLookupResponse>> {
  const id = `${country}:${compactId(businessId)}`;
  return shared(`card:${id}:${mode}:${preset}`, () =>
    attempt(
      () => api.lookupCard(country, businessId, mode, preset),
      async () => {
        const card = (await cardsOf(mode, preset))?.[id];
        const founder = (await snapshot<Record<string, FounderResponse>>("founder"))?.[id];
        return card && founder ? { lookup: founder.lookup, card } : null;
      },
      FORMAT_HINT[country],
    ),
  );
}

/** The live card again with the company's own website read. There is no offline reader. */
export function readCompanySite(
  country: Country,
  businessId: string,
  mode: Mode,
  preset: PresetName = "blue",
): Promise<Outcome<CardReadResponse>> {
  return shared(`read:${country}:${compactId(businessId)}:${mode}:${preset}`, () =>
    attempt(
      () => api.lookupCardRead(country, businessId, mode, preset),
      async () => null,
      FORMAT_HINT[country],
    ),
  );
}

/** Any company by name, in the registers and the precomputed set. There is no offline register search. */
export function searchCompanies(
  query: string,
  country?: Country,
): Promise<Outcome<SearchResponse>> {
  return shared(`search:${country ?? "any"}:${query}`, () =>
    attempt(
      () => api.search(query, country),
      async () => null,
      "Type at least 3 letters of the company name.",
    ),
  );
}

/** A partner's blind set, scored by the API in memory. There is no offline scorer. */
export async function scoreBlindSet(file: File): Promise<Outcome<PrecisionReport>> {
  const text = await file.text();
  const json = file.name.toLowerCase().endsWith(".json");
  return attempt(
    () => api.blindPrecision(text, json),
    async () => null,
    "The file could not be read.",
  );
}

/** null: sharing is not available right now (nothing was sent). */
export async function shareWithApelago(): Promise<ShareReceipt | null> {
  const outcome = await attempt(api.shareWithApelago, async () => null, "Sharing was refused.");
  return outcome.kind === "result" ? outcome.data : null;
}

// ---- the outreach desk (demo): live only; nothing is ever e-mailed, and there is no offline desk

const DESK_HINT = "The desk did not allow this step.";
const live = <T>(run: () => Promise<T>) => attempt(run, async () => null, DESK_HINT);

export const desk = {
  drafts: (): Promise<Outcome<DeskDraft[]>> => live(api.outreach.drafts),
  create: (companyId: string, mode: Mode, language: DraftLanguage = "en", bridgeId?: string) =>
    live(() => api.outreach.create(companyId, mode, language, bridgeId)),
  draft: (id: string): Promise<Outcome<DeskDraft>> => live(() => api.outreach.draft(id)),
  /** Approves the exact text the reviewer saw: pass the text_hash that came with the draft. */
  approve: (id: string, textHash: string) => live(() => api.outreach.approve(id, textHash)),
  /** The demo send: ends as blocked_demo; nothing leaves the server. */
  send: (id: string): Promise<Outcome<DeskDraft>> => live(() => api.outreach.send(id)),
  /** A simulated company reply that turns the asked unknowns into facts confirmed by the company. */
  reply: (id: string): Promise<Outcome<DeskReply>> => live(() => api.outreach.reply(id)),
  audit: (id: string): Promise<Outcome<AuditEvent[]>> => live(() => api.outreach.audit(id)),
  reset: () => live(api.outreach.reset),
};

export { FORMAT_HINT };
