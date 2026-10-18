// The form's answers as the visitor edits them, and the submission the API receives. Answers live in
// React state only: nothing here touches storage.
import { ApiError } from "../../api";
import { own, type Message } from "./message";
import type {
  Commitment,
  Exists,
  IdeaSubmission,
  Need,
  PresetName,
  Role,
  TeamCountry,
} from "../ideas/types";

export interface TeamRow {
  /** "" until a role is chosen; rows without a role are not sent. */
  role: Role | "";
  skills: string;
}

export interface Draft {
  title: string;
  problem: string;
  who_has_it: string;
  solution: string;
  who_pays: string;
  impact_area: string | null;
  exists: Exists[];
  exists_detail: string;
  needs: Need[];
  team: TeamRow[];
  commitment: Commitment | null;
  country: TeamCountry | null;
  /** One input shows at first; "Add a link" shows the next, up to three. */
  links: string[];
}

export type TextField =
  "title" | "problem" | "who_has_it" | "solution" | "who_pays" | "exists_detail";

export const EMPTY_DRAFT: Draft = {
  title: "",
  problem: "",
  who_has_it: "",
  solution: "",
  who_pays: "",
  impact_area: null,
  exists: [],
  exists_detail: "",
  needs: [],
  team: [{ role: "", skills: "" }],
  commitment: null,
  country: null,
  links: [""],
};

export function toSubmission(draft: Draft, preset: PresetName): IdeaSubmission {
  return {
    title: draft.title.trim(),
    problem: draft.problem.trim(),
    who_has_it: draft.who_has_it.trim(),
    solution: draft.solution.trim(),
    who_pays: draft.who_pays.trim(),
    impact_area: draft.impact_area,
    exists: draft.exists,
    exists_detail: draft.exists_detail.trim(),
    needs: draft.needs,
    team: draft.team.flatMap((row) =>
      row.role ? [{ role: row.role, skills: row.skills.trim() }] : [],
    ),
    commitment: draft.commitment,
    country: draft.country,
    links: draft.links.map((link) => link.trim()).filter(Boolean),
    preset,
  };
}

/** Two submissions are the same idea when they would send the same JSON. */
export function sameSubmission(a: IdeaSubmission, b: IdeaSubmission): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export type FieldErrors = Partial<Record<TextField | "links", Message>>;

/** The checks the browser makes before sending anything (IDEA-HARBOUR.md §3.4). */
export function clientErrors(draft: Draft): FieldErrors {
  const errors: FieldErrors = {};
  if (draft.title.trim().length < 3) errors.title = own("titleShort");
  if (!draft.problem.trim() && !draft.solution.trim()) errors.problem = own("problemOrSolution");
  const badLink = draft.links.some((link) => link.trim() && !isFullAddress(link));
  if (badLink) errors.links = own("fullAddress");
  return errors;
}

export function isFullAddress(link: string): boolean {
  return /^https?:\/\//i.test(link.trim());
}

const FIELDS: (TextField | "links")[] = [
  "title",
  "problem",
  "who_has_it",
  "solution",
  "who_pays",
  "exists_detail",
  "links",
];

/**
 * A 422 whose detail names a field ("problem: …", "submission links: …") belongs under that field;
 * anything else is a banner. Pydantic's "Value error, " prefix is noise for a visitor.
 */
export function fieldError(error: ApiError): { field: TextField | "links"; text: string } | null {
  if (error.status !== 422 || !error.detail) return null;
  const match = /^(?:submission )?([a-z_]+)(?: \d+)?: (.+)$/s.exec(error.detail);
  const field = FIELDS.find((f) => f === match?.[1]);
  if (!match || !field) return null;
  return { field, text: match[2].replace(/^Value error, /, "") };
}

/** The answers an error is about: "write the problem or the solution" is answered by either. */
const ERROR_SOURCES: Partial<Record<TextField | "links", (keyof Draft)[]>> = {
  problem: ["problem", "solution"],
};

/** An error stays under its field until the visitor changes what it was about. */
export function stillShown(errors: FieldErrors, checked: Draft, now: Draft): FieldErrors {
  const shown: FieldErrors = {};
  for (const field of FIELDS) {
    const sources = ERROR_SOURCES[field] ?? [field];
    const unchanged = sources.every(
      (key) => JSON.stringify(checked[key]) === JSON.stringify(now[key]),
    );
    if (errors[field] && unchanged) shown[field] = errors[field];
  }
  return shown;
}
