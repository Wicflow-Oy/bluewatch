// The night "Due next" card: the soonest dated step as a big day count, the next few below it.
import { getLang } from "../i18n/lang";
import { localeOf, useT } from "../i18n/messages";
import { CountUp } from "./CountUp";
import { deadlineInfo } from "./Deadline";
import { DeadlineList, type DeadlineItem } from "./DeadlineList";
import { uiMessages } from "./messages";
import "./DueNextCard.css";

interface DueNextCardProps {
  /** Any order; sorted soonest first, past items dropped. */
  items: DeadlineItem[];
  today: string;
  /** Rows under the hero, default 4. */
  laterLimit?: number;
  /** Eyebrow, default "Due next". */
  label?: string;
}

/** "Wed 28 Oct 2026" in the interface language. */
function longDay(iso: string): string {
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(localeOf(getLang()), {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function DueNextCard({ items, today, laterLimit = 4, label }: DueNextCardProps) {
  const { t, tn } = useT(uiMessages);
  const upcoming = items
    .filter((item) => !deadlineInfo(item.date, today).past)
    .sort((a, b) => a.date.localeCompare(b.date));
  const [hero, ...rest] = upcoming;
  const info = hero ? deadlineInfo(hero.date, today) : null;
  const days = info?.days ?? 0;

  return (
    <section className={`due-card${info?.soon ? " due-card--soon" : ""}`}>
      <p className="due-card__eyebrow">
        <span>{label ?? t("dueNext")}</span>
        {hero && <span className="due-card__date">{longDay(hero.date)}</span>}
      </p>
      {hero ? (
        <>
          <p className="due-card__big">
            {days === 0 ? (
              <span className="due-card__count">{t("dueToday")}</span>
            ) : (
              <>
                <span className="due-card__count">
                  <CountUp value={days} decimals={0} duration={1100} />
                </span>
                <span className="due-card__unit">{tn("unitDays", days)}</span>
              </>
            )}
          </p>
          {hero.href ? (
            <a className="due-card__what" href={hero.href}>
              {hero.title}
            </a>
          ) : (
            <p className="due-card__what">{hero.title}</p>
          )}
          {hero.detail && <p className="due-card__who">{hero.detail}</p>}
          {rest.length > 0 && (
            <div className="due-card__later">
              <DeadlineList variant="night" items={rest} today={today} limit={laterLimit} />
            </div>
          )}
        </>
      ) : (
        <p className="due-card__empty">{t("noDatedSteps")}</p>
      )}
    </section>
  );
}
