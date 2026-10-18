// The page title with the list's own meta line (week, since, count, data stamp, sources, rules) and the two
// header actions: the "Why these" popover and "Start review".
import type { ShortList } from "../../contracts";
import { useT } from "../../i18n/messages";
import { formatClock, formatStamp, formatStampDay } from "../../lib/format";
import { useMeta } from "../../lib/meta";
import { shellMessages } from "../../shell/messages";
import { PageHeader } from "../../ui/Panel";
import { Kbd } from "../../ui/States";
import { surfacingMessages } from "./messages";
import { WhyThesePopover } from "./WhyThesePopover";

/** The ISO 8601 week number of a calendar day. */
function isoWeek(iso: string): number {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day); // the Thursday of this week decides the year
  const yearStart = Date.UTC(d.getUTCFullYear(), 0, 1);
  return Math.ceil(((d.getTime() - yearStart) / 86_400_000 + 1) / 7);
}

interface SurfacingHeaderProps {
  list: ShortList;
  /** Moves the J/K cursor to the first visible row; undefined when no row is visible. */
  onStartReview?: () => void;
}

export function SurfacingHeader({ list, onStartReview }: SurfacingHeaderProps) {
  const { t, tn } = useT(surfacingMessages);
  const shell = useT(shellMessages);
  const meta = useMeta();
  const n = list.entries.length;
  const cap = list.cap ?? n;
  // A planned source is not connected yet, so it is neither counted nor reported as down.
  const sources = (list.sources ?? []).filter((s) => s.state !== "planned");
  const down = sources.filter((s) => s.state === "unavailable").length;

  const items = [
    <span key="week">{t("week", { n: isoWeek(meta.today) })}</span>,
    list.since && (
      <span key="since">
        {t("since", { when: `${formatStampDay(list.since)} ${formatClock(list.since)}` })}
      </span>
    ),
    <span key="count">
      <span aria-hidden="true">
        <b>{n}</b> / {cap}
      </span>
      <span className="sr-only">{tn("countSpoken", cap, { count: n })}</span>
    </span>,
    <span key="asof">
      {shell.t("dataAsOf")} {formatStamp(list.generated_at)}
    </span>,
    sources.length > 0 && (
      <span key="sources" className="surfacing__meta-sources">
        {down > 0 && <span className="surfacing__down-dot" aria-hidden="true" />}
        {t("sourcesUp", { up: sources.length - down, all: sources.length })}
        {down > 0 && <span className="sr-only">, {tn("sourcesDownSpoken", down)}</span>}
      </span>
    ),
    <span key="rules">{list.rules_version}</span>,
  ];

  return (
    <PageHeader
      title={meta.listName}
      meta={items}
      actions={
        n > 0 && (
          <>
            <WhyThesePopover list={list} />
            <button
              type="button"
              className="btn btn--primary"
              onClick={onStartReview}
              disabled={!onStartReview}
              aria-keyshortcuts="R"
            >
              {t("startReview")}
              <Kbd>R</Kbd>
            </button>
          </>
        )
      }
    />
  );
}
