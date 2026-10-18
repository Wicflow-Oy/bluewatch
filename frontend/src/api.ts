// Typed client for the BlueWatch API. All data comes from the server; no keys in the browser.
import type {
  Alert,
  AuditEvent,
  Bridge,
  CompanyRow,
  ContactPlan,
  DeskDraft,
  DeskReply,
  FounderView,
  FundingCatalogue,
  PrecisionReport,
  PresetInfo,
  Registry,
  ShortList,
  SourceStatus,
  VentureCard,
} from "./contracts";
import { getLang, withLang, type Lang } from "./i18n/lang";
import type { PresetName } from "./lib/preset";

export type Mode = "apelago" | "redstone";
export type Country = "FI" | "NO" | "EE";
export type DraftLanguage = "en" | "fi" | "sv";

export interface Meta {
  product_name: string;
  list_name: string;
  modes: Mode[];
  today: string;
  outreach_mode: string;
  live_lookups: boolean;
  contracts_version: string;
  /** The deployed commit (BLUEWATCH_BUILD), "dev" when unset; absent in the offline snapshot. */
  build?: string;
  group_labels: Record<string, string>;
  group_rule: string;
  tier_labels: Record<Mode, Record<string, string>>;
  level_labels: Record<Mode, Record<string, string>>;
  dimension_labels: Record<string, string>;
  attribution: string;
  live_reader: boolean;
}

/** Mirrors bluewatch/lookup.py LookupResult (not part of the generated contracts). */
export interface LookupResult {
  country: Country;
  business_id: string;
  found: boolean;
  natural_person: boolean;
  registry: Registry | null;
  /** The register lists the company as ceased, deleted, bankrupt or being wound up. */
  closed: boolean;
  company_id: string | null;
  status: SourceStatus;
  /** Live lookups are off here: only the recorded register data was searched. */
  recorded_only: boolean;
  message: string;
}

export interface FounderResponse {
  lookup: LookupResult;
  view: FounderView | null;
}

/** Mirrors bluewatch/sources/search.py SearchCandidate. business_id is "" for a precomputed company
 * without a register ID; company_id is set when the company is in the precomputed set. Closed companies
 * come last. */
export interface SearchCandidate {
  country: string;
  business_id: string;
  name: string;
  registered: string | null;
  form: string | null;
  municipality: string | null;
  status: string | null;
  /** The register lists it as ceased, deleted, bankrupt or being wound up. */
  closed: boolean;
  /** The former name, or another name in use, that the search matched. */
  formerly: string | null;
  also_known_as: string | null;
  company_id: string | null;
}

/** One status per register searched; more: there were more matches than shown. */
export interface SearchResponse {
  candidates: SearchCandidate[];
  sources: SourceStatus[];
  more: boolean;
}

/** card is null for a sole trader or an ID the register does not know. */
export interface CardLookupResponse {
  lookup: LookupResult;
  card: VentureCard | null;
}

/** Mirrors bluewatch/read/live.py SiteRead: how the company's own website was read for its live card. */
export interface SiteRead {
  state: "read" | "no_site" | "unreachable" | "timeout" | "budget" | "failed" | "off";
  host: string | null;
  url: string | null;
  read_at: string | null;
  /** false: found by the company's name, with ownership evidence on the page. */
  found_in_register: boolean;
  claims: number;
}

/** read is null for a company that has no live card (assessed already, a sole trader or not found). */
export interface CardReadResponse {
  lookup: LookupResult;
  card: VentureCard | null;
  read: SiteRead | null;
}

export interface ShareReceipt {
  demo: boolean;
  stored: boolean;
  message: string;
  at: string;
}

/** status 0 means the API was not reachable or did not answer with JSON. */
export class ApiError extends Error {
  readonly status: number;
  /** A human-readable message from our own API, when it sent one. */
  readonly detail: string | null;

  constructor(status: number, path: string, detail: string | null = null) {
    super(`${status || "unreachable"} ${path}`);
    this.status = status;
    this.detail = detail;
  }
}

/** Every request names the interface language: the API translates its prose (never quotes or names). */
async function request<T>(path: string, init?: RequestInit, lang: Lang = getLang()): Promise<T> {
  let res: Response;
  try {
    res = await fetch(withLang(path, lang), {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, path);
  }
  if (!res.ok) {
    throw new ApiError(res.status, path, await readDetail(res));
  }
  try {
    return (await res.json()) as T;
  } catch {
    // A dev server or proxy answering with HTML is the same as no API for the visitor.
    throw new ApiError(0, path);
  }
}

async function readDetail(res: Response): Promise<string | null> {
  try {
    const body: unknown = await res.json();
    const detail = (body as { detail?: unknown } | null)?.detail;
    return typeof detail === "string" ? detail : null;
  } catch {
    return null;
  }
}

function post<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

// The outreach desk keeps one in-memory desk per visitor, keyed by this random id. It lives in this tab's
// memory only, so a reload starts a fresh desk. getRandomValues, not randomUUID: the latter needs HTTPS.
const DESK_SESSION = {
  "X-Demo-Session": Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join(""),
};
const draftPath = (id: string, action = "") =>
  `/api/outreach/drafts/${encodeURIComponent(id)}${action}`;

export const api = {
  meta: (lang: Lang) => request<Meta>("/api/meta", undefined, lang),
  sources: () => request<SourceStatus[]>("/api/sources"),
  presets: () => request<PresetInfo[]>("/api/presets"),
  list: (mode: Mode, preset: PresetName = "blue") =>
    request<ShortList>(`/api/list?mode=${mode}&preset=${preset}`),
  companies: (mode: Mode, preset: PresetName = "blue") =>
    request<CompanyRow[]>(`/api/companies?mode=${mode}&preset=${preset}`),
  card: (companyId: string, mode: Mode, preset: PresetName = "blue") =>
    request<VentureCard>(
      `/api/companies/${encodeURIComponent(companyId)}?mode=${mode}&preset=${preset}`,
    ),
  bridges: (mode: Mode) => request<Bridge[]>(`/api/bridges?mode=${mode}`),
  bridge: (bridgeId: string, mode: Mode) =>
    request<Bridge>(`/api/bridges/${encodeURIComponent(bridgeId)}?mode=${mode}`),
  funding: (mode: Mode) => request<FundingCatalogue>(`/api/funding?mode=${mode}`),
  alerts: (mode: Mode) => request<Alert[]>(`/api/alerts?mode=${mode}`),
  precision: () => request<PrecisionReport>("/api/precision"),
  /** The partner's file goes in the body (never the URL) and is scored in memory only. */
  blindPrecision: (text: string, json: boolean) =>
    request<PrecisionReport>("/api/precision/blind", {
      method: "POST",
      headers: { "Content-Type": json ? "application/json" : "text/csv" },
      body: text,
    }),
  scout: (mode: Mode, topN = 20) => request<ContactPlan[]>(`/api/scout?top_n=${topN}&mode=${mode}`),
  founder: (country: Country, businessId: string) =>
    post<FounderResponse>("/api/founder", { country, business_id: businessId }),
  lookupCard: (country: Country, businessId: string, mode: Mode, preset: PresetName = "blue") =>
    post<CardLookupResponse>("/api/lookup/card", {
      country,
      business_id: businessId,
      mode,
      preset,
    }),
  /** The same card with the company's website read: slower, so it follows lookupCard. */
  lookupCardRead: (country: Country, businessId: string, mode: Mode, preset: PresetName = "blue") =>
    post<CardReadResponse>("/api/lookup/card/read", {
      country,
      business_id: businessId,
      mode,
      preset,
    }),
  /** The name goes in the body (never the URL) and is never stored. */
  search: (query: string, country?: Country) =>
    post<SearchResponse>("/api/search", { query, country }),
  shareWithApelago: () => post<ShareReceipt>("/api/founder/share"),
  outreach: {
    drafts: () => request<DeskDraft[]>("/api/outreach/drafts", { headers: DESK_SESSION }),
    /** `bridgeId`: the bridge the draft is about; without it, the company's best bridge or opportunity. */
    create: (companyId: string, mode: Mode, language: DraftLanguage = "en", bridgeId?: string) =>
      post<DeskDraft>(
        "/api/outreach/drafts",
        { company_id: companyId, mode, language, bridge_id: bridgeId ?? null },
        DESK_SESSION,
      ),
    draft: (id: string) => request<DeskDraft>(draftPath(id), { headers: DESK_SESSION }),
    approve: (id: string, textHash: string) =>
      post<DeskDraft>(draftPath(id, "/approve"), { text_hash: textHash }, DESK_SESSION),
    send: (id: string) => post<DeskDraft>(draftPath(id, "/send"), undefined, DESK_SESSION),
    reply: (id: string) => post<DeskReply>(draftPath(id, "/reply"), undefined, DESK_SESSION),
    audit: (id: string) =>
      request<AuditEvent[]>(draftPath(id, "/audit"), { headers: DESK_SESSION }),
    reset: () => post<{ reset: boolean }>("/api/outreach/reset", undefined, DESK_SESSION),
  },
};
