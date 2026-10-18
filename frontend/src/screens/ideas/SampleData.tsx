// The sample-data preview: a switch between the live queue and invented ideas, a banner that stays on
// screen for as long as the sample shows, and a chip on every sample item, so nothing invented can be
// mistaken for a real submission.
import { FlaskConical } from "lucide-react";
import { useT } from "../../i18n/messages";
import { Segmented } from "../../ui/Segmented";
import { ideasMessages } from "./messages";
import type { QueueSource } from "./useQueue";

const SOURCES: QueueSource[] = ["live", "sample"];

export function QueueSourceSwitch({
  value,
  onChange,
}: {
  value: QueueSource;
  onChange: (source: QueueSource) => void;
}) {
  const { t } = useT(ideasMessages);
  return (
    <Segmented<QueueSource>
      size="sm"
      label={t("queueSource")}
      value={value}
      onChange={onChange}
      options={SOURCES.map((source) => ({ value: source, label: t(`source_${source}`) }))}
    />
  );
}

export function SampleBanner({ onLive }: { onLive: () => void }) {
  const { t } = useT(ideasMessages);
  return (
    <div className="callout callout--amber ih-sample-banner" role="status">
      <FlaskConical aria-hidden="true" />
      <p>{t("sampleBanner")}</p>
      <button type="button" className="btn btn--sm" onClick={onLive}>
        {t("backToLive")}
      </button>
    </div>
  );
}

export function SampleChip() {
  const { t } = useT(ideasMessages);
  return (
    <span className="ih-sample-chip">
      <FlaskConical size={12} strokeWidth={1.75} aria-hidden="true" />
      {t("sampleChip")}
    </span>
  );
}
