// Idea Harbour, A'Pelago's side (#/ideas): ideas shared from the student form and real pre-company
// leads from public data, read by one rubric, with a Top N that is never padded.
import { BookOpen, ExternalLink } from "lucide-react";
import { useState } from "react";
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import { usePreset } from "../../lib/preset";
import { href } from "../../lib/router";
import { useWorkspace } from "../../lib/workspace";
import { shellMessages } from "../../shell/messages";
import { PageHeader } from "../../ui/Panel";
import { NO_FILTERS, type Filters } from "./filters";
import { Harbour, useQueueCounts } from "./Harbour";
import { IdeaCardDrawer } from "./IdeaCard";
import { ideasMessages } from "./messages";
import { QueueFailed, QueueSkeleton } from "./QueueStates";
import { closeItem } from "./queueRow";
import { DEFAULT_TOP_N } from "./api";
import { BELOW_DESKTOP, PHONE, useMedia } from "./read/hooks";
import { RubricDrawer } from "./RubricDrawer";
import { QueueSourceSwitch, SampleBanner } from "./SampleData";
import { useQueue, type QueueSource } from "./useQueue";
import "./read/read.css";
import "./ideas.css";

const TOP_CHOICES = [3, 5, 10];

export function IdeasScreen({ itemId }: { itemId?: string }) {
  const { t } = useT(ideasMessages);
  const shell = useT(shellMessages);
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const meta = useMeta();
  const phone = useMedia(PHONE);
  // Seven columns need a desktop; below it the rows stack as cards.
  const stacked = useMedia(BELOW_DESKTOP);
  // Always opens on the live queue: the sample is a preview someone chooses, never a remembered state.
  const [source, setSource] = useState<QueueSource>("live");
  const [topN, setTopN] = useState(DEFAULT_TOP_N);
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [rubricOpen, setRubricOpen] = useState(false);
  const { queue, failed, retry } = useQueue(source, mode, preset, topN);
  const sample = source === "sample";
  const counts = useQueueCounts(queue, sample);
  const showLive = () => setSource("live");

  return (
    <div className="page ih-page">
      <PageHeader
        title={shell.t("page_ideas")}
        meta={counts}
        explainer={t("explainer")}
        actions={
          <div className="ih-actions">
            <QueueSourceSwitch value={source} onChange={setSource} />
            <a className="btn" href={href({ name: "apply", preset })}>
              <ExternalLink size={16} strokeWidth={1.5} aria-hidden="true" />
              {t("openStudentForm")}
            </a>
            <button type="button" className="btn btn--ghost" onClick={() => setRubricOpen(true)}>
              <BookOpen size={16} strokeWidth={1.5} aria-hidden="true" />
              {t("howWeVet")}
            </button>
            <select
              className="select"
              aria-label={t("topChoiceLabel")}
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
            >
              {TOP_CHOICES.map((n) => (
                <option key={n} value={n}>
                  {t("topN", { n })}
                </option>
              ))}
            </select>
          </div>
        }
      />

      {sample && <SampleBanner onLive={showLive} />}

      {queue ? (
        <Harbour
          queue={queue}
          sample={sample}
          preset={preset}
          filters={filters}
          onFilters={setFilters}
          phone={phone}
          stacked={stacked}
          today={meta.today}
          keyboard={itemId === undefined && !rubricOpen}
        />
      ) : failed ? (
        <QueueFailed source={source} onRetry={retry} onLive={showLive} />
      ) : (
        <QueueSkeleton topN={topN} />
      )}

      <IdeaCardDrawer
        itemId={itemId}
        queue={queue}
        sample={sample}
        today={meta.today}
        onClose={() => closeItem(itemId)}
      />
      <RubricDrawer
        open={rubricOpen}
        onClose={() => setRubricOpen(false)}
        baseRateNote={queue?.base_rate_note ?? null}
      />
    </div>
  );
}
