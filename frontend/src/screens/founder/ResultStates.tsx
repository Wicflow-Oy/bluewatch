// What the results area shows when there is no company view: before the first lookup, while it runs,
// a sole trader (nothing at all), a company that no longer trades, an ID the register doesn't know, an ID
// outside the recorded data while live lookups are off, a register that couldn't answer, or a lookup that
// failed. None of them is ever shown as zero.
import {
  ArrowUpRight,
  Banknote,
  CalendarClock,
  CloudOff,
  DatabaseZap,
  DoorClosed,
  Gavel,
  RefreshCw,
  SearchX,
  TriangleAlert,
  UserRoundX,
} from "lucide-react";
import type { Country } from "../../api";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { href } from "../../lib/router";
import { Panel } from "../../ui/Panel";
import { EmptyState, ErrorState, LoadingRegion, Skeleton, SkeletonLines } from "../../ui/States";
import { founderMessages } from "./messages";

export function ResultPreview() {
  const { t } = useT(founderMessages);
  const lines = [
    { icon: Gavel, text: t("previewTiers") },
    { icon: Banknote, text: t("previewFits") },
    { icon: CalendarClock, text: t("previewNext") },
  ];
  return (
    <Panel className="founder-preview" title={t("previewTitle")}>
      <ul className="founder-preview__lines">
        {lines.map(({ icon: Icon, text }) => (
          <li key={text}>
            <Icon size={16} strokeWidth={1.5} aria-hidden="true" />
            {text}
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export function ResultSkeleton() {
  const { t } = useT(founderMessages);
  return (
    <LoadingRegion label={t("loading")}>
      <div className="founder-result">
        <Panel className="founder-profile">
          <Skeleton width={260} height={32} radius={8} />
          <div className="founder-facts founder-facts--skeleton">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} height={36} radius={8} />
            ))}
          </div>
        </Panel>
        <Panel className="founder-result__next" title={t("nextTitle")}>
          <SkeletonLines lines={4} gap={16} />
        </Panel>
        <Panel className="founder-result__investors" title={t("investorsTitle")}>
          <SkeletonLines lines={4} gap={16} />
        </Panel>
        <Panel className="founder-result__tiers" title={t("tiersTitle")}>
          <SkeletonLines lines={5} gap={16} />
        </Panel>
      </div>
    </LoadingRegion>
  );
}

export function SoleTrader() {
  const { t } = useT(founderMessages);
  return (
    <Panel className="founder-sole">
      <EmptyState
        compact
        icon={<UserRoundX size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("soleTraderTitle")}
      >
        {t("soleTraderBody")}
      </EmptyState>
    </Panel>
  );
}

/** The register lists the company as closed: its profile stays, and the API's sentence says why nothing
 * else is shown. */
export function NoLongerTrading({ message }: { message: string }) {
  const { t } = useT(founderMessages);
  return (
    <Panel className="founder-closed">
      <EmptyState
        compact
        icon={<DoorClosed size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("closedTitle")}
      >
        {message}
      </EmptyState>
    </Panel>
  );
}

/** The assessed company's card, when the ID is in the assessed set without a register record. */
function OpenCard({ companyId }: { companyId: string | null }) {
  const { t } = useT(founderMessages);
  if (!companyId) return null;
  return (
    <a className="btn" href={href({ name: "card", companyId })}>
      {t("openCard")}
      <ArrowUpRight size={14} strokeWidth={1.5} aria-hidden="true" />
    </a>
  );
}

export function NotInRegister({ companyId }: { companyId: string | null }) {
  const { t } = useT(founderMessages);
  return (
    <Panel>
      <EmptyState
        compact
        icon={<SearchX size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("notFoundTitle")}
        action={<OpenCard companyId={companyId} />}
      >
        {t("notFoundBody")}
      </EmptyState>
    </Panel>
  );
}

/** Live lookups are off and the ID isn't in the recorded data: a setting, so there is nothing to retry,
 * and the company may still exist. */
export function NotRecorded({ companyId }: { companyId: string | null }) {
  const { t } = useT(founderMessages);
  return (
    <Panel>
      <EmptyState
        compact
        icon={<DatabaseZap size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("notRecordedTitle")}
        action={<OpenCard companyId={companyId} />}
      >
        {t("notRecordedBody")}
      </EmptyState>
    </Panel>
  );
}

function RetryButton({ onRetry }: { onRetry(): void }) {
  const { t } = useT(founderMessages);
  return (
    <button type="button" className="btn" onClick={onRetry}>
      <RefreshCw size={14} strokeWidth={1.5} aria-hidden="true" />
      {t("tryAgain")}
    </button>
  );
}

interface RegisterDownProps {
  country: Country;
  /** The connector's reason, which always says the result was not counted as zero. */
  detail?: string;
  onRetry(): void;
}

/** The register (or our API) couldn't answer: say so, and never treat it as "not found". */
export function RegisterDown({ country, detail, onRetry }: RegisterDownProps) {
  const { t } = useT(founderMessages);
  const register = t(`register_${country}`);
  return (
    <Panel className="founder-down">
      <ErrorState
        compact
        icon={<CloudOff size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("registerDownTitle")}
        action={<RetryButton onRetry={onRetry} />}
      >
        {detail ? (
          <>
            <p>{t("registerDownRetry", { register })}</p>
            <p className="founder-down__reason">
              {t("registerDownReason", { detail: humanText(detail) })}
            </p>
          </>
        ) : (
          t("registerDown", { register })
        )}
      </ErrorState>
    </Panel>
  );
}

export function LookupFailed({ onRetry }: { onRetry(): void }) {
  const { t } = useT(founderMessages);
  return (
    <Panel>
      <ErrorState
        compact
        icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("failedTitle")}
        action={<RetryButton onRetry={onRetry} />}
      >
        {t("failedBody")}
      </ErrorState>
    </Panel>
  );
}
