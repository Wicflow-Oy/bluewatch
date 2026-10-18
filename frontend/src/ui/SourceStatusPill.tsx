import type { ReactNode } from "react";
import type { SourceStatus } from "../contracts";
import { useT } from "../i18n/messages";
import { formatStamp } from "../lib/format";
import { shortSourceName, sourceStateLabel } from "../lib/labels";
import { uiMessages } from "./messages";
import { Tooltip } from "./Tooltip";
import "./SourceStatusPill.css";

export function SourceStatusTip({ status }: { status: SourceStatus }) {
  const { t } = useT(uiMessages);
  const when = status.checked_at ?? status.data_as_of;
  return (
    <>
      <div className="tooltip__title">{status.label}</div>
      <p className="muted">
        {sourceStateLabel(status.state)}
        {status.detail ? `: ${status.detail}` : ""}
      </p>
      {when && when.length > 10 && (
        <p className="tooltip__note">{t("asOf", { stamp: formatStamp(when) })}</p>
      )}
      {status.state === "unavailable" && <p className="tooltip__note">{t("sourceMissingNote")}</p>}
    </>
  );
}

export function SourceStatusPill({ status }: { status: SourceStatus }) {
  const { t } = useT(uiMessages);
  const down = status.state === "unavailable";
  return (
    <Tooltip content={<SourceStatusTip status={status} />} placement="bottom">
      <span className={`source-pill source-pill--${status.state}`} tabIndex={0}>
        <span className="source-pill__dot" aria-hidden="true" />
        <span className="source-pill__name">{shortSourceName(status.label)}</span>
        <span className="source-pill__state">
          {down ? t("sourceDown") : sourceStateLabel(status.state)}
        </span>
        <span className="sr-only">{status.detail}</span>
      </span>
    </Tooltip>
  );
}

/** One dot per source. */
export function SourceDots({ sources }: { sources: SourceStatus[] }) {
  const { t } = useT(uiMessages);
  return (
    <ul className="source-dots" aria-label={t("sourceStatus")}>
      {sources.map((s) => (
        <li key={s.source}>
          <Tooltip content={<SourceStatusTip status={s} />} placement="right">
            <span className={`source-dot source-dot--${s.state}`} tabIndex={0}>
              <span className="sr-only">{`${s.label}: ${sourceStateLabel(s.state)}`}</span>
            </span>
          </Tooltip>
        </li>
      ))}
    </ul>
  );
}

/** "Company register (PRH)" -> name "Company register", code "PRH". */
function splitLabel(label: string): { name: string; code: string | null } {
  const m = /^(.*?)\s*\(([^)]+)\)\s*$/.exec(label);
  return m ? { name: m[1], code: m[2] } : { name: label, code: null };
}

/** Every source as a row with its state, sources that did not answer first (rail and status popover). */
export function SourceRows({
  sources,
  attribution,
}: {
  sources: SourceStatus[];
  attribution?: ReactNode;
}) {
  const { t } = useT(uiMessages);
  const rank = (s: SourceStatus) => (s.state === "unavailable" ? 0 : s.state === "planned" ? 2 : 1);
  const ordered = [...sources].sort((a, b) => rank(a) - rank(b));
  return (
    <div className="source-rows">
      <ul aria-label={t("sourceStatus")}>
        {ordered.map((s) => {
          const { name, code } = splitLabel(s.label);
          const down = s.state === "unavailable";
          return (
            <li key={s.source}>
              <Tooltip content={<SourceStatusTip status={s} />} placement="bottom">
                <span className={`source-row source-row--${s.state}`} tabIndex={0}>
                  <span className="source-row__dot" aria-hidden="true" />
                  <span className="source-row__name">
                    {name}
                    {code && <span className="source-row__code mono"> {code}</span>}
                  </span>
                  <span className="source-row__state mono">{sourceStateLabel(s.state)}</span>
                  {down && <span className="source-row__note">{t("sourceMissingNote")}</span>}
                </span>
              </Tooltip>
            </li>
          );
        })}
      </ul>
      {attribution && <p className="source-rows__attribution">{attribution}</p>}
    </div>
  );
}
