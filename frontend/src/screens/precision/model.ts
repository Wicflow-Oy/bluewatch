// What the Precision screen derives from a PrecisionReport. Pure functions: no React, no fetching.
import type { Mode } from "../../api";
import type { LevelAgreement, PrecisionReport, TrapResult } from "../../contracts";

export type LevelKey = LevelAgreement["key"];

const LEVEL_ORDER: LevelKey[] = ["trl", "brl", "irl", "oirl"];

export function orderedLevels(report: PrecisionReport): LevelAgreement[] {
  const levels = report.levels ?? [];
  return LEVEL_ORDER.flatMap((key) => levels.filter((level) => level.key === key));
}

/** What agreeing means for a level: the same band of the 1-9 scale (1-3, 4-6, 7-9), or for investment
 * readiness the same stage (pre-seed, seed, Series A or later). See bluewatch/evals/precision.py. */
export function agreementUnit(key: LevelKey): "band" | "stage" {
  return key === "irl" ? "stage" : "band";
}

export interface Comparison {
  key: LevelKey;
  ours: number;
  baseline: number;
  n: number;
}

export interface BaselineVerdict {
  baselineAhead: Comparison[];
  oursAhead: Comparison[];
  tied: Comparison[];
}

/** Every level with answer keys and a baseline, sorted by who agrees with the key more often. */
export function compareWithBaseline(levels: LevelAgreement[]): BaselineVerdict {
  const verdict: BaselineVerdict = { baselineAhead: [], oursAhead: [], tied: [] };
  for (const level of levels) {
    const baseline = level.baseline_exact;
    if (level.n === 0 || baseline === null || baseline === undefined) continue;
    const row = { key: level.key, ours: level.exact, baseline, n: level.n };
    if (baseline > level.exact) verdict.baselineAhead.push(row);
    else if (level.exact > baseline) verdict.oursAhead.push(row);
    else verdict.tied.push(row);
  }
  return verdict;
}

/** Inside a sentence: "business readiness", with the acronym in Redstone mode ("business readiness (BRL)"). */
export function sentenceLabel(key: LevelKey, apelagoLabel: string, mode: Mode): string {
  const words = apelagoLabel.charAt(0).toLowerCase() + apelagoLabel.slice(1);
  return mode === "redstone" ? `${words} (${key.toUpperCase()})` : words;
}

export function failedFirst(traps: TrapResult[]): TrapResult[] {
  return [...traps].sort((a, b) => Number(a.passed) - Number(b.passed));
}

// ---- stage words, as the scorer writes them (bluewatch/evals/keys.py STAGES)

const STAGE_KEYS = {
  "pre-seed": "stage_preSeed",
  seed: "stage_seed",
  "Series A or later": "stage_seriesA",
} as const;

export type StageKey = (typeof STAGE_KEYS)[keyof typeof STAGE_KEYS];

/** "pre-seed to seed" -> its stage keys; null for a value that isn't stage words ("4-6", "7"). */
export function stageKeys(value: string): StageKey[] | null {
  const keys = value.split(" to ").map((word) => STAGE_KEYS[word as keyof typeof STAGE_KEYS]);
  return keys.every(Boolean) ? keys : null;
}

// ---- a partner's blind set

export type Verdict = "same band" | "within one" | "differs";
export type PartnerLevel = "TRL" | "BRL" | "stage";

export interface PartnerCall {
  ours: string;
  theirs: string;
  verdict: Verdict | null;
}

export interface PartnerRow {
  name: string;
  /** False when the company is not among our assessments. */
  matched: boolean;
  calls: Partial<Record<PartnerLevel, PartnerCall>>;
}

// "Partner row Kelluu: TRL ours unknown / yours 7-9; BRL ours 2 / yours 6-7 (differs)." (evals/blind.py).
// These rows come from an upload, so the API never translates them and the English pattern holds.
const PARTNER_NOTE = /^Partner row (.+?): (.*)\.$/;
const PARTNER_CALL =
  /^(TRL|BRL|stage) ours (.+?) \/ yours (.+?)(?: \((same band|within one|differs)\))?$/;

/** The side-by-side rows of a blind-set report; notes that aren't partner rows are skipped. */
export function partnerRows(notes: string[]): PartnerRow[] {
  return notes.flatMap((note): PartnerRow[] => {
    const m = PARTNER_NOTE.exec(note);
    if (!m) return [];
    const [, name, body] = m;
    if (body === "not in our assessments") return [{ name, matched: false, calls: {} }];
    const calls: PartnerRow["calls"] = {};
    for (const part of body.split("; ")) {
      const call = PARTNER_CALL.exec(part);
      if (call) {
        const level = call[1] as PartnerLevel;
        calls[level] = { ours: call[2], theirs: call[3], verdict: (call[4] as Verdict) ?? null };
      }
    }
    return [{ name, matched: true, calls }];
  });
}

export type BlindProblem = "fileType" | "fileSize" | "noIdColumn" | "noRows" | "unreadableJson";

const BLIND_MAX_BYTES = 200 * 1024;
// The columns the scorer names a row by (bluewatch/evals/blind.py); a file without one would score
// nameless rows instead of failing.
const NAME_COLUMNS = ["company", "name", "id"];

/** Why a file can't be sent, judged from its name and size alone. */
export function fileProblem(file: File): BlindProblem | null {
  if (!/\.(csv|json)$/i.test(file.name)) return "fileType";
  if (file.size > BLIND_MAX_BYTES) return "fileSize";
  return null;
}

/** Why a file's text can't be scored, or null when it can be sent. */
export function contentProblem(text: string, json: boolean): BlindProblem | null {
  return json ? jsonProblem(text) : csvProblem(text);
}

function csvProblem(text: string): BlindProblem | null {
  const lines = text
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "" && !line.trimStart().startsWith("#"));
  if (lines.length === 0) return "noRows";
  const header = lines[0].split(",").map((cell) => cell.trim().replace(/^"|"$/g, "").toLowerCase());
  if (!header.some((cell) => NAME_COLUMNS.includes(cell))) return "noIdColumn";
  return lines.length > 1 ? null : "noRows";
}

function jsonProblem(text: string): BlindProblem | null {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return "unreadableJson";
  }
  const records = Array.isArray(data) ? data : isRecord(data) ? data.companies : null;
  if (!Array.isArray(records) || !records.every(isRecord)) return "unreadableJson";
  if (records.length === 0) return "noRows";
  const named = records.every((record) =>
    Object.keys(record).some((key) => NAME_COLUMNS.includes(key.trim().toLowerCase())),
  );
  return named ? null : "noIdColumn";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
