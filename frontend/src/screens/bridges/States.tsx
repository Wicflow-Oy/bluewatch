// The page while bridges load, when they can't load, and when a link names a bridge this workspace lacks.
import { RefreshCw, Unlink, Waypoints } from "lucide-react";
import { useT } from "../../i18n/messages";
import { WORKSPACES } from "../../lib/labels";
import { href } from "../../lib/router";
import type { Mode } from "../../api";
import { Panel } from "../../ui/Panel";
import { EmptyState, ErrorState, LoadingRegion, Skeleton, SkeletonLines } from "../../ui/States";
import { BridgesHeader } from "./BridgesHeader";
import { bridgesMessages } from "./messages";

const ICON = { size: 20, strokeWidth: 1.5, "aria-hidden": true } as const;

export function NoBridges() {
  const { t } = useT(bridgesMessages);
  return (
    <EmptyState icon={<Waypoints {...ICON} />} title={t("emptyTitle")}>
      {t("emptyBody")}
    </EmptyState>
  );
}

export function BridgeNotHere({ mode }: { mode: Mode }) {
  const { t } = useT(bridgesMessages);
  return (
    <EmptyState
      icon={<Unlink {...ICON} />}
      title={t("notHereTitle", { name: WORKSPACES[mode].name })}
      action={
        <a className="btn" href={href({ name: "bridges" })}>
          {t("showStrongest")}
        </a>
      }
    >
      {t("notHereBody")}
    </EmptyState>
  );
}

export function BridgesUnavailable() {
  const { t } = useT(bridgesMessages);
  return (
    <div className="page bridges">
      <BridgesHeader />
      <Panel className="bridges__unavailable">
        <ErrorState
          compact
          icon={<Waypoints {...ICON} />}
          title={t("unavailableTitle")}
          action={
            <button type="button" className="btn" onClick={() => window.location.reload()}>
              <RefreshCw size={14} strokeWidth={1.5} aria-hidden="true" />
              {t("retry")}
            </button>
          }
        >
          {t("unavailableBody")}
        </ErrorState>
      </Panel>
    </div>
  );
}

/** The hero's real split (company, connector, counterparty) with grey bars for the values. */
export function BridgesSkeleton() {
  const { t } = useT(bridgesMessages);
  return (
    <div className="page bridges">
      <BridgesHeader />
      <LoadingRegion label={t("loading")}>
        <div className="bridges__stack">
          <Panel className="bridge-hero">
            <Skeleton width={240} height={16} />
            <Skeleton width="56%" height={16} style={{ marginTop: 16 }} />
            <div className="bridge-hero__grid bridge-hero__grid--skeleton">
              {(["company", "counterparty"] as const).map((side) => (
                <div key={side} className={`bridge-party bridge-party--${side}`}>
                  <Skeleton width={72} height={12} />
                  <Skeleton width={200} height={28} radius={8} style={{ marginTop: 8 }} />
                </div>
              ))}
              {(["company", "counterparty"] as const).map((side) => (
                <div key={side} className={`bridge-evidence bridge-evidence--${side}`}>
                  <div className="bridge-evidence__item">
                    <SkeletonLines lines={3} />
                  </div>
                </div>
              ))}
              <div className="bridge-link">
                <span className="bridge-link__type">
                  <Skeleton width={120} height={12} />
                </span>
                <span className="bridge-link__when">
                  <Skeleton width={220} height={32} radius={8} />
                </span>
              </div>
            </div>
          </Panel>
          <Panel title={t("otherBridges")}>
            <SkeletonLines lines={5} gap={24} />
          </Panel>
        </div>
      </LoadingRegion>
    </div>
  );
}
