// Dated next actions, soonest first: a month/day block, what to do, and a countdown. "night" is the dark
// variant inside the Due next card.
import { getLang } from "../i18n/lang";
import { localeOf } from "../i18n/messages";
import { deadlineInfo } from "./Deadline";
import "./DeadlineList.css";

export interface DeadlineItem {
  date: string;
  title: string;
  detail?: string;
  href?: string;
}

interface DeadlineListProps {
  items: DeadlineItem[];
  today: string;
  limit?: number;
  variant?: "plain" | "night";
}

/** "OCT" and "28" for an ISO day, in the interface language. */
export function monthDay(iso: string): { month: string; day: string } {
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return { month: "", day: iso };
  const locale = localeOf(getLang());
  return {
    month: new Intl.DateTimeFormat(locale, { month: "short", timeZone: "UTC" })
      .format(date)
      .replace(".", ""),
    day: new Intl.DateTimeFormat(locale, { day: "numeric", timeZone: "UTC" })
      .format(date)
      .replace(".", ""),
  };
}

export function DeadlineList({ items, today, limit, variant = "plain" }: DeadlineListProps) {
  const shown = [...items].sort((a, b) => a.date.localeCompare(b.date)).slice(0, limit);
  return (
    <ol className={`deadline-list deadline-list--${variant}`}>
      {shown.map((item) => (
        <li key={`${item.date}|${item.title}`}>
          <DeadlineRow item={item} today={today} />
        </li>
      ))}
    </ol>
  );
}

function DeadlineRow({ item, today }: { item: DeadlineItem; today: string }) {
  const d = deadlineInfo(item.date, today);
  const md = monthDay(item.date);
  const body = (
    <>
      <span className="deadline-list__when" aria-label={d.day}>
        <span className="deadline-list__month" aria-hidden="true">
          {md.month}
        </span>
        <span className="deadline-list__day" aria-hidden="true">
          {md.day}
        </span>
      </span>
      <span className="deadline-list__what">
        <span className="deadline-list__title">{item.title}</span>
        {item.detail && <span className="deadline-list__detail">{item.detail}</span>}
      </span>
      <span className={`deadline-list__count${d.soon ? " deadline-list__count--soon" : ""}`}>
        {d.countdown}
      </span>
    </>
  );
  return item.href ? (
    <a className="deadline-list__item" href={item.href} title={item.title}>
      {body}
    </a>
  ) : (
    <div className="deadline-list__item" title={item.title}>
      {body}
    </div>
  );
}
