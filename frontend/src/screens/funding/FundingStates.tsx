// The page's frame and the states around the catalogue: loading, failed, and no listed company.
import { RefreshCw, TriangleAlert, Wallet } from "lucide-react";
import { Component, type ReactNode } from "react";
import type { Mode } from "../../api";
import { useT } from "../../i18n/messages";
import { shellMessages } from "../../shell/messages";
import { PageHeader, Panel } from "../../ui/Panel";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "../../ui/States";
import { fundingMessages } from "./messages";
import { RulesDisclosure, RulesPanel } from "./TierRules";

export function FundingHeader({ actions }: { actions?: ReactNode }) {
  const { t } = useT(fundingMessages);
  const shell = useT(shellMessages);
  return (
    <PageHeader title={shell.t("page_funding")} explainer={t("explainer")} actions={actions} />
  );
}

export function FundingSkeleton({ mode }: { mode: Mode }) {
  const { t } = useT(fundingMessages);
  return (
    <>
      <FundingHeader
        actions={
          <span className="funding__picker">
            <Skeleton height={36} radius={999} />
          </span>
        }
      />
      <LoadingRegion label={t("loading")}>
        <RulesDisclosure mode={mode} />
        <Panel title={t("flipTitle")} className="flip">
          <Skeleton width="60%" height={14} />
          <div className="flip__grid flip__grid--loading">
            <Skeleton height={232} radius={20} />
            <Skeleton height={64} radius={16} />
            <Skeleton height={232} radius={20} />
          </div>
        </Panel>
        <div className="funding__body">
          <section className="funding__tiers" aria-label={t("tiers")}>
            <Skeleton width={360} height={30} radius={999} />
            {[0, 1, 2].map((group) => (
              <div className="funding__group funding__group-skeleton" key={group}>
                <Skeleton width={240} height={22} radius={999} />
                <Skeleton height={72} radius={16} />
                <Skeleton height={72} radius={16} />
              </div>
            ))}
          </section>
          <RulesPanel mode={mode} />
        </div>
      </LoadingRegion>
    </>
  );
}

export function NoCompanyState() {
  const { t } = useT(fundingMessages);
  return (
    <>
      <FundingHeader />
      <Panel>
        <EmptyState
          compact
          icon={<Wallet size={20} strokeWidth={1.5} aria-hidden="true" />}
          title={t("noCompanyTitle")}
        >
          {t("noCompanyBody")}
        </EmptyState>
      </Panel>
    </>
  );
}

/** A failed catalogue (not a missing one: that falls back to the recording) keeps the page's frame. */
export class FundingBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? <FundingError /> : this.props.children;
  }
}

function FundingError() {
  const { t } = useT(fundingMessages);
  return (
    <>
      <FundingHeader />
      <Panel>
        <ErrorState
          icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
          title={t("errorTitle")}
          action={
            <>
              {/* A reload, because the data layer keeps a failed request for the session. */}
              <button type="button" className="btn" onClick={() => window.location.reload()}>
                <RefreshCw size={14} strokeWidth={1.5} aria-hidden="true" />
                {t("retry")}
              </button>
              <a className="btn btn--ghost" href="#/founder">
                {t("openFounder")}
              </a>
            </>
          }
        >
          {t("errorBody")}
        </ErrorState>
      </Panel>
    </>
  );
}
