// Every source with its freshness. A source that failed comes first and is never hidden: its rows are
// missing, not zero, and the list says so instead of reporting a quiet week.
import { CircleCheck } from "lucide-react";
import { useId } from "react";
import type { SourceStatus } from "../contracts";
import { useT } from "../i18n/messages";
import { uiMessages } from "./messages";
import { SourceStatusPill } from "./SourceStatusPill";
import "./SourceStrip.css";

export function SourceStrip({ sources }: { sources: SourceStatus[] }) {
  const { t, tn } = useT(uiMessages);
  const labelId = useId();
  const down = sources.filter((s) => s.state === "unavailable");
  const planned = sources.filter((s) => s.state === "planned");
  const connected = sources.filter((s) => s.state !== "unavailable" && s.state !== "planned");
  const ordered = [...down, ...connected, ...planned];
  return (
    <div className="source-strip">
      <span className="overline source-strip__label" id={labelId}>
        {t("sources")}
      </span>
      <ul className="source-strip__pills" aria-labelledby={labelId}>
        {ordered.map((s) => (
          <li key={s.source}>
            <SourceStatusPill status={s} />
          </li>
        ))}
        {sources.length === 0 && <li className="source-strip__none">{t("sourcesNotReported")}</li>}
        {down.length === 0 && connected.length > 0 && (
          <li className="source-strip__ok">
            <CircleCheck size={14} strokeWidth={1.5} aria-hidden="true" />
            {tn("sourcesAnswered", connected.length)}
          </li>
        )}
      </ul>
    </div>
  );
}
