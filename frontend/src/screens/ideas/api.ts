// Idea Harbour API client. Failures throw the shared ApiError, so screens handle them like the rest.
import { ApiError, type Mode } from "../../api";
import { withLang } from "../../i18n/lang";
import type {
  IdeaAssessment,
  IdeaForm,
  IdeaQueue,
  IdeaSubmission,
  PresetName,
  RubricInfo,
  SessionShares,
  ShareReceipt,
  ShareRequest,
  WithdrawReceipt,
} from "./types";

const SESSION_KEY = "bluewatch.demo-session";
/** The Top N the queue opens on (and the sidebar counts). */
export const DEFAULT_TOP_N = 5;
let memoryId: string | null = null;

/**
 * One random id per browser tab, made in the browser and sent as X-Demo-Session. It is the only thing
 * that ties a shared idea to this visitor, and the server forgets it after 60 minutes.
 */
export function demoSessionId(): string {
  try {
    const existing = sessionStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
    return id;
  } catch {
    // Storage blocked (private mode, previews): keep the id for this page load only.
    memoryId ??= crypto.randomUUID();
    return memoryId;
  }
}

const session = (): Record<string, string> => ({ "X-Demo-Session": demoSessionId() });

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(withLang(path), {
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
    throw new ApiError(0, path);
  }
}

/** Our API's message; for a 422 from field validation, the first field and what is wrong with it. */
async function readDetail(res: Response): Promise<string | null> {
  try {
    const body: unknown = await res.json();
    const detail = (body as { detail?: unknown } | null)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { loc?: unknown[]; msg?: unknown };
      const field = (first.loc ?? []).filter((part) => part !== "body").join(" ");
      return typeof first.msg === "string" ? `${field}: ${first.msg}` : null;
    }
    return null;
  } catch {
    return null;
  }
}

function post<T>(path: string, body?: unknown, headers: Record<string, string> = {}): Promise<T> {
  return call<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export const ideasApi = {
  form: (preset: PresetName = "blue") => call<IdeaForm>(`/api/ideas/form?preset=${preset}`),
  rubric: () => call<RubricInfo>("/api/ideas/rubric"),
  /**
   * The readiness read. Nothing is stored. aiRead is the "Claude may read our answers too" toggle: only
   * then does the text go to Anthropic's API (and only if the server allows it; see reader_note).
   */
  vet: (submission: IdeaSubmission, aiRead: boolean) =>
    post<IdeaAssessment>("/api/ideas/vet", { ...submission, ai_read: aiRead }),
  /** Only after the visitor ticks the consent box. The server reads the idea again, with the same choice. */
  share: (submission: IdeaSubmission, aiRead: boolean, consentTextVersion: string) => {
    const body: ShareRequest = {
      submission: { ...submission, ai_read: aiRead },
      consent: true,
      consent_text_version: consentTextVersion,
    };
    return post<ShareReceipt>("/api/ideas/share", body, session());
  },
  withdraw: () => post<WithdrawReceipt>("/api/ideas/withdraw", undefined, session()),
  /** Whether this browser session still has shared ideas, so a reloaded page can offer Withdraw. */
  shared: () => call<SessionShares>("/api/ideas/shared", { headers: session() }),
  /** The live queue, or with sample the sample-data preview (invented ideas, never mixed with live ones). */
  queue: (
    mode: Mode,
    preset: PresetName = "blue",
    topN = DEFAULT_TOP_N,
    { sample = false }: { sample?: boolean } = {},
  ) =>
    call<IdeaQueue>(
      `/api/ideas/queue?mode=${mode}&preset=${preset}&top_n=${topN}${sample ? "&sample=1" : ""}`,
      { headers: session() },
    ),
};
