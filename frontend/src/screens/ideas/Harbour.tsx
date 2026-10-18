// The loaded queue: what is in it, the top slots, the filters and the ranked list.
import { Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { useT } from "../../i18n/messages";
import { formatStamp } from "../../lib/format";
import { href } from "../../lib/router";
import { uiMessages } from "../../ui/messages";
import { EmptyState } from "../../ui/States";
import { FilterBar } from "./FilterBar";
import { activeCount, facetCounts, inQueue, matches, NO_FILTERS, type Filters } from "./filters";
import { ideasMessages } from "./messages";
import { QueueList } from "./QueueList";
import { FIGURE_SLOT, withSlots } from "./read/slots";
import { TopSlots } from "./TopSlots";
import type { IdeaQueue, PresetName } from "./types";

interface HarbourProps {
  queue: IdeaQueue;
  sample: boolean;
  preset: PresetName;
  filters: Filters;
  onFilters: (filters: Filters) => void;
  phone: boolean;
  stacked: boolean;
  today: string;
  keyboard: boolean;
}

export function Harbour({
  queue,
  sample,
  preset,
  filters,
  onFilters,
  phone,
  stacked,
  today,
  keyboard,
}: HarbourProps) {
  const { t } = useT(ideasMessages);
  const counts = facetCounts(queue.items);
  const active = inQueue(filters, counts);
  const shown = queue.items.filter((item) => matches(item, active));
  return (
    <div className="ih-harbour">
      <TopSlots queue={queue} sample={sample} />
      <FilterBar
        counts={counts}
        filters={active}
        onChange={onFilters}
        shown={shown.length}
        total={queue.items.length}
        folded={phone}
      />
      {!sample && queue.session_items === 0 && (
        <p className="callout ih-nothing-shared">
          <Inbox aria-hidden="true" />
          <span>
            {withSlots(t("nothingShared"), {
              form: <a href={href({ name: "apply", preset })}>{t("studentFormLink")}</a>,
            })}
          </span>
        </p>
      )}
      {shown.length > 0 ? (
        <QueueList
          queue={queue}
          items={shown}
          stacked={stacked}
          today={today}
          sample={sample}
          keyboard={keyboard}
        />
      ) : (
        <EmptyState
          compact
          icon={<Inbox size={20} strokeWidth={1.5} aria-hidden="true" />}
          title={t("noMatches")}
          action={
            activeCount(active) > 0 && (
              <button type="button" className="btn btn--sm" onClick={() => onFilters(NO_FILTERS)}>
                {t("clearFilters")}
              </button>
            )
          }
        />
      )}
    </div>
  );
}

/**
 * "29 in the queue · 12 hackathon results · …" for the page header's mono meta line (one node per phrase,
 * so the header puts its dots between them).
 */
export function useQueueCounts(queue: IdeaQueue | null, sample: boolean): ReactNode[] | undefined {
  const { tn } = useT(ideasMessages);
  const ui = useT(uiMessages);
  if (!queue) return undefined;
  const count = (key: string) => queue.counts[key] ?? 0;
  const phrase = (base: Parameters<typeof tn>[0], n: number) => (
    <span key={base}>{withSlots(tn(base, n, FIGURE_SLOT), { n: <b>{n}</b> })}</span>
  );
  return [
    phrase("inQueue", count("total")),
    phrase(sample ? "sampleIdeas" : "sharedThisSession", count("your_submission")),
    phrase("hackathonResults", count("hackathon_result")),
    phrase("researchProjects", count("research_project")),
    phrase("held", count("held")),
    <span key="asof">{withSlots(ui.t("asOf"), { stamp: formatStamp(queue.generated_at) })}</span>,
  ];
}
