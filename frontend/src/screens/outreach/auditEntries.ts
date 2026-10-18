// The desk's audit events worded for a reader. The desk logs keys and short structured notes
// ("route org_generic; text c1424634ea6e"); the parts the screen knows become words in the interface
// language, and anything else (the sending rules' own reasons) is shown as the desk wrote it.
import type { AuditEvent } from "../../contracts";
import { humanText } from "../../lib/format";
import type { AuditEntry, AuditTone } from "../../ui/AuditTrail";
import { answeredWords, languageLabel, modeLabel, routeLabel } from "./labels";
import type { OutreachT, OutreachText } from "./messages";

const ACTIONS = [
  "drafted",
  "submitted",
  "submit_blocked",
  "edited",
  "approved",
  "approval_refused",
  "approval_blocked",
  "approval_void",
  "rejected",
  "public_demo",
  "send_blocked",
  "send_refused",
  "send_failed",
  "sent",
  "reply_answer",
  "reply_opt_out",
  "reply_bounce",
  "reply_other",
] as const;
type Action = (typeof ACTIONS)[number];

// The desk names its approver "demo reviewer" because a visitor's name is never asked for.
const APPROVER = "demo reviewer";
const SIMULATED_COMPANY = "reply";
const WARNING = /refused|blocked|failed|void/;

const DRAFTED = /^(\w+), (\w+), (.+)$/;
const ANSWERED = /^answered (\d+) of (\d+) questions$/;
const ROUTE = /^route (\w+)$/;
const TEXT_HASH = /^text ([0-9a-f]{12})$/;

const isAction = (action: string): action is Action =>
  (ACTIONS as readonly string[]).includes(action);

export function auditEntries(events: AuditEvent[], text: OutreachText): AuditEntry[] {
  const { t } = text;
  return events.map((event) => ({
    at: event.at,
    action: isAction(event.action) ? t(`action_${event.action}`) : humanText(event.action),
    actor: actorLabel(event.actor, t),
    detail: event.detail ? detailWords(event.action, event.detail, text) : null,
    tone: toneOf(event),
  }));
}

function actorLabel(actor: string, t: OutreachT): string {
  if (actor === APPROVER) return t("actor_you");
  if (actor === SIMULATED_COMPANY) return t("actor_company");
  return "BlueWatch";
}

function toneOf(event: AuditEvent): AuditTone {
  if (WARNING.test(event.action)) return "warning";
  if (event.actor === APPROVER) return "you";
  if (event.actor === SIMULATED_COMPANY) return "company";
  return "system";
}

function detailWords(action: string, detail: string, text: OutreachText): string {
  const { t } = text;
  if (action === "public_demo") return t("publicDemoDetail");
  const drafted = action === "drafted" ? DRAFTED.exec(detail) : null;
  if (drafted) {
    const [, mode, language, note] = drafted;
    return [modeLabel(t, mode), languageLabel(t, language), noteWords(note, t)].join(" · ");
  }
  return detail
    .split(/\s*;\s*/)
    .filter(Boolean)
    .map((part) => partWords(part, text))
    .join(" · ");
}

function noteWords(note: string, t: OutreachT): string {
  if (note === "template") return t("note_template");
  if (note === "polished") return t("note_polished");
  return humanText(note);
}

function partWords(part: string, text: OutreachText): string {
  const { t } = text;
  const route = ROUTE.exec(part);
  if (route) return t("detailRoute", { route: routeLabel(t, route[1]) });
  const hash = TEXT_HASH.exec(part);
  if (hash) return t("detailHash", { hash: `${hash[1]}…` });
  const answered = ANSWERED.exec(part);
  if (answered) return answeredWords(Number(answered[1]), Number(answered[2]), text);
  return humanText(part);
}
