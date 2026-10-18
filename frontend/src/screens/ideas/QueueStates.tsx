// The queue while it loads, and when it can't: the live queue points to the student form, the sample
// preview back to the live queue.
import { RefreshCw, TriangleAlert } from "lucide-react";
import { useT } from "../../i18n/messages";
import { ErrorState, LoadingRegion, Skeleton } from "../../ui/States";
import { ideasMessages } from "./messages";
import type { QueueSource } from "./useQueue";

interface QueueFailedProps {
  source: QueueSource;
  onRetry: () => void;
  onLive: () => void;
}

export function QueueFailed({ source, onRetry, onLive }: QueueFailedProps) {
  const { t } = useT(ideasMessages);
  const sample = source === "sample";
  return (
    <ErrorState
      icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
      title={t(sample ? "sampleUnavailable" : "queueFailed")}
      action={
        sample ? (
          <button type="button" className="btn" onClick={onLive}>
            {t("backToLive")}
          </button>
        ) : (
          <button type="button" className="btn" onClick={onRetry}>
            <RefreshCw size={16} strokeWidth={1.5} aria-hidden="true" />
            {t("retry")}
          </button>
        )
      }
    />
  );
}

export function QueueSkeleton({ topN }: { topN: number }) {
  const { t } = useT(ideasMessages);
  return (
    <LoadingRegion label={t("loadingQueue")}>
      <div className="ih-harbour">
        <section className="ih-top">
          <h2 className="ih-section-title">{t("topTitle", { n: topN })}</h2>
          <ol className="ih-slots" data-count={topN}>
            {Array.from({ length: topN }, (_, i) => (
              <li key={i} className="ih-slot capsule">
                <Skeleton width={32} height={14} />
                <Skeleton width="80%" height={16} />
                <Skeleton width="50%" height={20} radius={999} />
              </li>
            ))}
          </ol>
        </section>
        <div className="ih-skeleton-rows">
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} className="ih-skeleton-row capsule">
              <Skeleton width={40} height={40} radius={12} />
              <Skeleton width="60%" height={14} />
              <Skeleton width="50%" height={20} radius={999} />
              <Skeleton width="70%" height={14} />
            </div>
          ))}
        </div>
      </div>
    </LoadingRegion>
  );
}
