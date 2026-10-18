// What the desk shows instead of a draft: a company outside the assessed set, a company not yet matched
// with certainty, a desk that is down, a draft that failed, and a draft the sending rules refused.
import { CloudOff, RefreshCw, SearchX, ShieldAlert, TriangleAlert } from "lucide-react";
import type { Company } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { Panel } from "../../ui/Panel";
import { EmptyState, ErrorState } from "../../ui/States";
import { outreachMessages } from "./messages";

const ICON = { size: 20, strokeWidth: 1.5, "aria-hidden": true } as const;

export function NotAssessed() {
  const { t } = useT(outreachMessages);
  return (
    <Panel>
      <EmptyState compact icon={<SearchX {...ICON} />} title={t("notAssessedTitle")}>
        {t("notAssessedBody")}
      </EmptyState>
    </Panel>
  );
}

export function Unmatched({ company }: { company: Company }) {
  const { t } = useT(outreachMessages);
  const { state, reason } = company.resolution;
  const name = company.names[0] ?? company.id;
  return (
    <Panel className="outreach-unmatched">
      <EmptyState compact icon={<ShieldAlert {...ICON} />} title={t("unmatchedTitle")}>
        {t(`match_${state}`, { name, reason: humanText(reason) })} {t("matchRule")}
      </EmptyState>
    </Panel>
  );
}

export function DeskUnavailable() {
  const { t } = useT(outreachMessages);
  return (
    <Panel className="outreach-unavailable">
      <ErrorState compact icon={<CloudOff {...ICON} />} title={t("unavailableTitle")}>
        {t("unavailableBody")}
      </ErrorState>
    </Panel>
  );
}

export function DraftFailed({ onRetry }: { onRetry(): void }) {
  const { t } = useT(outreachMessages);
  return (
    <Panel>
      <ErrorState
        compact
        icon={<TriangleAlert {...ICON} />}
        title={t("failedTitle")}
        action={
          <button type="button" className="btn" onClick={onRetry}>
            <RefreshCw size={14} strokeWidth={1.5} aria-hidden="true" />
            {t("retry")}
          </button>
        }
      >
        {t("failedBody")}
      </ErrorState>
    </Panel>
  );
}

/** The desk's own reason, as it wrote it. */
export function DraftRefused({ message }: { message: string }) {
  const { t } = useT(outreachMessages);
  return (
    <Panel className="outreach-refused">
      <ErrorState compact icon={<ShieldAlert {...ICON} />} title={t("cantGoOut")}>
        {message}
      </ErrorState>
    </Panel>
  );
}
