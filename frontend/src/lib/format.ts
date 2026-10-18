// Dates and numbers in the interface language. English dates are written by hand rather than with Intl
// month names, because en-GB prints "Sept" and the product copy uses "Sep"; Finnish and Swedish use Intl.
// Times are shown in Helsinki time, where the teams work.
import type { Mode } from "../api";
import { getLang } from "../i18n/lang";
import { localeOf, translator } from "../i18n/messages";
import { formatMessages } from "./messages";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const DAY_MS = 86_400_000;

const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})$/;
const ISO_MONTH = /^(\d{4})-(\d{2})$/;

function dayParts(iso: string): [number, number, number] | null {
  const m = ISO_DAY.exec(iso.slice(0, 10));
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

function utcDay(iso: string): number | null {
  const p = dayParts(iso);
  return p ? Date.UTC(p[0], p[1] - 1, p[2]) : null;
}

/** Whole days from `today` to `iso` (both calendar days). */
export function daysUntil(iso: string, today: string): number | null {
  const a = utcDay(today);
  const b = utcDay(iso);
  return a === null || b === null ? null : Math.round((b - a) / DAY_MS);
}

/** Calendar days are UTC midnights here, so Intl must not shift them into another day. */
function intlDay(time: number, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat(localeOf(), { ...options, timeZone: "UTC" }).format(time);
}

/** "30 Oct" / "30.10." / "30 okt.", with the year when asked or when it is not the current year. */
export function formatDay(iso: string, opts: { year?: boolean; today?: string } = {}): string {
  const p = dayParts(iso);
  if (!p) return iso;
  const [y, m, d] = p;
  const thisYear = opts.today ? Number(opts.today.slice(0, 4)) : y;
  const withYear = opts.year || y !== thisYear;
  const lang = getLang();
  if (lang === "en") return `${d} ${MONTHS[m - 1]}${withYear ? ` ${y}` : ""}`;
  return intlDay(Date.UTC(y, m - 1, d), {
    day: "numeric",
    month: lang === "fi" ? "numeric" : "short",
    year: withYear ? "numeric" : undefined,
  });
}

/** "Sat" / "la" / "lör". */
export function weekday(iso: string): string {
  const t = utcDay(iso);
  if (t === null) return "";
  return getLang() === "en" ? WEEKDAYS[new Date(t).getUTCDay()] : intlDay(t, { weekday: "short" });
}

/** Event dates arrive as a day, a month or a free range ("2025-2026", "Mar-Apr 2025"). */
export function formatEventDate(value: string | null | undefined, today?: string): string | null {
  if (!value) return null;
  if (ISO_DAY.test(value.slice(0, 10)) && value.length >= 10)
    return formatDay(value, { year: true, today });
  const month = ISO_MONTH.exec(value);
  if (!month) return value;
  const [year, index] = [Number(month[1]), Number(month[2]) - 1];
  if (getLang() === "en") return `${MONTHS[index]} ${year}`;
  return intlDay(Date.UTC(year, index, 1), { month: "long", year: "numeric" });
}

export function formatYear(iso: string | null | undefined): string | null {
  return iso ? iso.slice(0, 4) : null;
}

const helsinki = new Intl.DateTimeFormat("en-US", {
  timeZone: "Europe/Helsinki",
  year: "numeric",
  month: "numeric",
  day: "numeric",
  weekday: "short",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

/** The Helsinki calendar day ("2026-10-17") and clock ("08:24", or "08.24" in Finnish), or null. */
function helsinkiParts(
  isoDateTime: string,
): { day: string; clock: string; clockSeconds: string } | null {
  const date = new Date(isoDateTime);
  if (Number.isNaN(date.getTime())) return null;
  const parts = Object.fromEntries(helsinki.formatToParts(date).map((p) => [p.type, p.value]));
  const pad = (value: string) => value.padStart(2, "0");
  const sep = getLang() === "fi" ? "." : ":";
  const clock = `${parts.hour}${sep}${parts.minute}`;
  return {
    day: `${parts.year}-${pad(parts.month)}-${pad(parts.day)}`,
    clock,
    clockSeconds: `${clock}${sep}${pad(parts.second)}`,
  };
}

/** "Sat 17 Oct 08:24" in Helsinki time, in the interface language. */
export function formatStamp(isoDateTime: string): string {
  const parts = helsinkiParts(isoDateTime);
  if (!parts) return isoDateTime;
  return `${weekday(parts.day)} ${formatDay(parts.day)} ${parts.clock}`;
}

/** "08:24" in Helsinki time; with seconds "08:24:05" ("08.24.05" in Finnish). */
export function formatClock(isoDateTime: string, opts: { seconds?: boolean } = {}): string {
  const parts = helsinkiParts(isoDateTime);
  if (!parts) return "";
  return opts.seconds ? parts.clockSeconds : parts.clock;
}

/** "17 Oct" / "17.10." / "17 okt.": the Helsinki calendar day of a timestamp. */
export function formatStampDay(isoDateTime: string): string {
  const parts = helsinkiParts(isoDateTime);
  return parts ? formatDay(parts.day) : isoDateTime;
}

/** English only: prefer tn() with _one/_other messages in new code. */
export function pluralise(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

const REGISTRY_BY_COUNTRY: Record<string, string> = {
  FI: "PRH",
  NO: "Brreg",
  EE: "RIK",
  SE: "SCB",
};

/** Norwegian organisation numbers are written in groups of three: "938 525 420". */
export function formatBusinessId(country: string, id: string): string {
  const digits = id.replace(/\s/g, "");
  return country === "NO" && /^\d{9}$/.test(digits)
    ? digits.replace(/^(\d{3})(\d{3})(\d{3})$/, "$1 $2 $3")
    : id.trim();
}

const noRegisterId = () => translator(formatMessages).t("noRegisterId");

/** "PRH 3652359-1", "Brreg 938 525 420", "RIK 12345678"; an empty ID says so. */
export function registryLabel(country: string, id: string): string {
  if (!id.trim()) return noRegisterId();
  return `${registryName(country)} ${formatBusinessId(country, id)}`;
}

/** A company id ("FI:3652359-1") as its register label; slug ids ("SE:candela-ab") hold no register ID. */
export function companyIdLabel(companyId: string): string {
  const [country, id = ""] = companyId.split(":");
  return /\d/.test(id) ? registryLabel(country, id) : noRegisterId();
}

export function registryName(country: string): string {
  return REGISTRY_BY_COUNTRY[country] ?? country;
}

// ---- numbers and backend text

// Float error would otherwise floor 0.29 to 0.28 (0.29 * 100 = 28.999999999999996).
const FLOAT_SLACK = 1e-9;

/** Floors to `digits` decimals; float error never takes a value one step down. */
export function floorTo(value: number, digits: number): number {
  const factor = 10 ** digits;
  return Math.floor(value * factor + FLOAT_SLACK) / factor;
}

/** Floors, never rounds: a score of 0.975 reads "0.97" ("0,97" in Finnish and Swedish), never "0.98". */
export function trunc(value: number, digits = 2): string {
  const fixed = floorTo(value, digits).toFixed(digits);
  return getLang() === "en" ? fixed : fixed.replace(".", ",");
}

/** "9 of 18" / "9/18" / "9 av 18". */
export function ofN(k: number, n: number): string {
  return translator(formatMessages).t("ofN", { k, n });
}

const SNAKE_WORDS: Record<string, string> = {
  data_digital: "data and digital",
  aquaculture_food: "aquaculture and food",
};

/** Backend keys inside prose ("ocean_observation; marine_sensors") read as words: "ocean observation, marine sensors". */
export function humanText(text: string): string {
  return text
    .replace(/\b[a-z0-9]+(?:_[a-z0-9]+)+\b/g, (key) => SNAKE_WORDS[key] ?? key.replace(/_/g, " "))
    .replace(/\s*;\s*/g, ", ");
}

const LEVEL_ACRONYM = /\b(TRL|BRL|IRL) (\d(?:-\d)?)/g;
// The ocean impact level, as the API writes it in each language: "(level 1)", "(taso 1)", "(nivå 1)".
const IMPACT_LEVEL = /\s*\((?:level|taso|nivå) \d\)/g;

/** Readiness levels inside backend text, as the workspace says them. A'Pelago uses words and no ocean
 * impact number: "published pricing (BRL 4)" reads "published pricing (business readiness level 4)".
 * Redstone keeps the acronyms. */
export function levelText(text: string, mode: Mode): string {
  if (mode === "redstone") return text;
  const { t } = translator(formatMessages);
  return text
    .replace(IMPACT_LEVEL, "")
    .replace(LEVEL_ACRONYM, (_, key: "TRL" | "BRL" | "IRL", n: string) => t(`level_${key}`, { n }));
}

/** 200000 -> "200k", 2000000 -> "2M", 1250000 -> "1.25M"; floored, so a ticket never reads larger. */
function euroAmount(eur: number): string {
  const lang = getLang();
  const decimal = (value: number) =>
    lang === "en" ? String(value) : String(value).replace(".", ",");
  // Finnish and Swedish write "200 k€" and "1,25 M€"; English writes "€200k" and "€1.25M".
  const [k, m] = lang === "en" ? ["k", "M"] : ["\u00a0k€", "\u00a0M€"];
  if (eur >= 1_000_000) return `${decimal(floorTo(eur / 1_000_000, 2))}${m}`;
  if (eur >= 1_000) return `${Math.floor(eur / 1_000 + FLOAT_SLACK)}${k}`;
  return lang === "en" ? String(eur) : `${eur}\u00a0€`;
}

/** An investor ticket: "€200k–2M", "from €500k", "up to €2M" or "Ticket not stated", in the interface language. */
export function money(min: number | null | undefined, max: number | null | undefined): string {
  const { t } = translator(formatMessages);
  const hasMin = typeof min === "number";
  const hasMax = typeof max === "number";
  if (hasMin && hasMax) return t("ticketRange", { min: euroAmount(min), max: euroAmount(max) });
  if (hasMin) return t("ticketFrom", { amount: euroAmount(min) });
  if (hasMax) return t("ticketUpTo", { amount: euroAmount(max) });
  return t("ticketNotStated");
}

/** The host of a URL, for "no public link" vs "havnio.no" style hints. */
export function hostOf(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}
