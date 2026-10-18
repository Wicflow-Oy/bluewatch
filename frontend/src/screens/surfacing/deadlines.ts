// The rail's "Due next": each listed company's dated next step, plus the alert deadlines that
// concern listed companies. The alerts API repeats one deadline per company, so alerts are grouped by
// what to do and when, and a company's own row is dropped when such a group already covers it.
import type { Alert, ListEntry } from "../../contracts";
import { daysUntil, humanText } from "../../lib/format";
import { href } from "../../lib/router";
import type { DeadlineItem } from "../../ui/DeadlineList";

const DEADLINE_WINDOW_DAYS = 45;

/** The words around the API's prose, in the reader's language. */
export interface DeadlineWording {
  entryTitle(company: string, action: string): string;
  groupDetail(companies: number): string;
}

interface AlertGroup {
  action: string;
  date: string;
  companyIds: string[];
}

function groupAlerts(alerts: Alert[], listed: Set<string>): AlertGroup[] {
  const groups = new Map<string, AlertGroup>();
  for (const a of alerts) {
    if (!a.deadline || !listed.has(a.company_id)) continue;
    const key = `${a.trigger}|${a.next_action}|${a.deadline}`;
    const group = groups.get(key) ?? { action: a.next_action, date: a.deadline, companyIds: [] };
    if (!group.companyIds.includes(a.company_id)) group.companyIds.push(a.company_id);
    groups.set(key, group);
  }
  return [...groups.values()];
}

const companyHref = (companyId: string) => href({ name: "surfacing", companyId });

export function deadlineItems(
  entries: ListEntry[],
  alerts: Alert[],
  today: string,
  wording: DeadlineWording,
): DeadlineItem[] {
  const listed = new Set(entries.map((e) => e.company_id));
  const groups = groupAlerts(alerts, listed);
  const covered = (e: ListEntry) =>
    groups.some(
      (g) =>
        g.date === e.deadline && g.action === e.next_action && g.companyIds.includes(e.company_id),
    );

  const fromEntries: DeadlineItem[] = entries.flatMap((e) =>
    e.deadline && !covered(e)
      ? [
          {
            date: e.deadline,
            title: wording.entryTitle(e.name, humanText(e.next_action)),
            href: companyHref(e.company_id),
          },
        ]
      : [],
  );

  const fromAlerts: DeadlineItem[] = groups.map((g) => ({
    date: g.date,
    title: humanText(g.action),
    detail: wording.groupDetail(g.companyIds.length),
    href: g.companyIds.length === 1 ? companyHref(g.companyIds[0]) : undefined,
  }));

  const seen = new Set<string>();
  return [...fromEntries, ...fromAlerts].filter((item) => {
    const days = daysUntil(item.date, today);
    const key = `${item.title}|${item.date}`;
    if (days === null || days < 0 || days > DEADLINE_WINDOW_DAYS || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
