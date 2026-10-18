// The card's loading, not-found and error states. Each keeps the card's real shape, so nothing jumps
// when the data lands, and each says what still works.
import { RefreshCw, SearchX, TriangleAlert } from "lucide-react";
import { Component, type ReactNode } from "react";
import { useT } from "../../i18n/messages";
import { pageHref } from "../../lib/router";
import { Panel } from "../../ui/Panel";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "../../ui/States";
import { cardMessages } from "./messages";

export function HeaderSkeleton() {
  return (
    <div className="entity-skeleton" aria-hidden="true">
      <Skeleton width={56} height={56} radius={16} />
      <div className="entity-skeleton__text">
        <Skeleton width={260} height={30} radius={8} />
        <Skeleton width="70%" height={14} />
        <div className="entity-skeleton__chips">
          <Skeleton width={88} height={22} radius={11} />
          <Skeleton width={112} height={22} radius={11} />
          <Skeleton width={96} height={22} radius={11} />
        </div>
      </div>
    </div>
  );
}

/** The overview's three columns, in their real panels, so nothing jumps when the card lands. */
export function OverviewSkeleton() {
  const { t } = useT(cardMessages);
  return (
    <LoadingRegion label={t("loadingCard")}>
      <div className="overview overview--steps">
        <div className="overview__col">
          <Panel title={t("potentialAndEvidence")}>
            <div className="dual">
              <Skeleton height={168} radius={16} />
              <Skeleton height={168} radius={16} />
            </div>
          </Panel>
          <Panel title={t("readiness")}>
            <div className="skeleton-rows">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} height={44} radius={8} />
              ))}
            </div>
          </Panel>
        </div>
        <div className="overview__col">
          <Panel title={t("whatWeKnow")}>
            <div className="skeleton-rows">
              <Skeleton height={60} radius={14} />
              <Skeleton height={116} radius={10} />
              <Skeleton height={40} radius={8} />
            </div>
          </Panel>
        </div>
        <div className="overview__col overview__col--steps">
          <Panel title={t("nextStepsInOrder")}>
            <div className="skeleton-rows">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} height={84} radius={8} />
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </LoadingRegion>
  );
}

export function RailSkeleton() {
  const { t } = useT(cardMessages);
  return (
    <Panel title={t("nextStepsInOrder")}>
      <div className="skeleton-rows" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={96} radius={8} />
        ))}
      </div>
    </Panel>
  );
}

export function NotInSet() {
  const { t } = useT(cardMessages);
  return (
    <EmptyState
      icon={<SearchX size={20} strokeWidth={1.5} aria-hidden="true" />}
      title={t("notInSetTitle")}
      action={
        <a className="btn" href={pageHref("founder")}>
          {t("lookUpById")}
        </a>
      }
    >
      {t("notInSetBody")}
    </EmptyState>
  );
}

function CardError() {
  const { t } = useT(cardMessages);
  return (
    <ErrorState
      icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
      title={t("cardErrorTitle")}
      action={
        <button type="button" className="btn" onClick={() => window.location.reload()}>
          <RefreshCw size={14} strokeWidth={1.5} aria-hidden="true" />
          {t("retry")}
        </button>
      }
    >
      {t("cardErrorBody")}
    </ErrorState>
  );
}

interface BoundaryProps {
  children: ReactNode;
  /** The sheet's close and full-page buttons stay reachable when the card fails. */
  actions?: ReactNode;
}

/** Keeps a failed card inside its sheet or page, so the list behind it stays usable. */
export class CardBoundary extends Component<BoundaryProps, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <>
        {this.props.actions && (
          <div className="venture-card__head venture-card__head--bare">{this.props.actions}</div>
        )}
        <div className="venture-card__state">
          <CardError />
        </div>
      </>
    );
  }
}
