import { translator, useT } from "../i18n/messages";
import { daysUntil, formatDay } from "../lib/format";
import { uiMessages } from "./messages";
import "./Deadline.css";

/** Deadlines within two weeks are amber, as they are in the list and on every card. */
export const SOON_DAYS = 14;

export function deadlineInfo(iso: string, today: string) {
  const { t, tn } = translator(uiMessages);
  const days = daysUntil(iso, today);
  return {
    day: formatDay(iso, { today }),
    days,
    soon: days !== null && days >= 0 && days <= SOON_DAYS,
    past: days !== null && days < 0,
    countdown:
      days === null
        ? ""
        : days < 0
          ? t("deadlineClosed")
          : days === 0
            ? t("deadlineToday")
            : tn("days", days),
  };
}

interface DeadlineProps {
  date: string | null | undefined;
  today: string;
  size?: "sm" | "lg";
  /** Show the countdown ("13 days") next to the date. */
  countdown?: boolean;
}

export function Deadline({ date, today, size = "sm", countdown = true }: DeadlineProps) {
  const { t } = useT(uiMessages);
  // In words, not a dash: the spec bans em dashes and a dash reads as missing data.
  if (!date) return <span className="deadline deadline--none">{t("noDeadline")}</span>;
  const d = deadlineInfo(date, today);
  // Years ahead read better as a date than as a day count.
  const showCount = countdown && d.days !== null && d.days <= 365;
  return (
    <span
      className={`deadline mono deadline--${size}${d.soon ? " deadline--soon" : ""}${d.past ? " deadline--past" : ""}`}
    >
      <span className="deadline__day">{d.day}</span>
      {showCount && <span className="deadline__count">{d.countdown}</span>}
    </span>
  );
}
