// The list's loading shape: the real title, pill-shaped filters, sheet rows and the rail's three cards.
import { useT } from "../../i18n/messages";
import { Panel, PageHeader } from "../../ui/Panel";
import { sonarMessages } from "../../ui/SonarPlot.messages";
import { LoadingRegion, Skeleton, SkeletonLines } from "../../ui/States";
import { surfacingMessages } from "./messages";

const SKELETON_ROWS = 8;

export function SurfacingSkeleton({ title }: { title: string }) {
  const { t } = useT(surfacingMessages);
  const sonar = useT(sonarMessages);
  return (
    <LoadingRegion label={t("loading", { list: title })}>
      <PageHeader title={title} meta={<Skeleton width={420} height={12} />} />
      <div className="surfacing__toolbar">
        <Skeleton width={360} height={42} radius={999} style={{ maxWidth: "100%" }} />
      </div>
      <div className="surfacing__layout">
        <div className="shortlist sheet">
          {Array.from({ length: SKELETON_ROWS }, (_, r) => (
            <div key={r} className="shortlist__skeleton-row">
              <Skeleton width={16} height={10} />
              <Skeleton width={150} height={12} />
              <Skeleton width={110} height={12} />
              <Skeleton height={12} />
            </div>
          ))}
        </div>
        <aside className="surfacing__rail">
          <div className="surfacing__due-skeleton" />
          <Panel title={sonar.t("sonar")}>
            <div className="surfacing__sonar-skeleton" />
          </Panel>
          <Panel title={t("sources")}>
            <SkeletonLines lines={4} gap={14} />
          </Panel>
        </aside>
      </div>
    </LoadingRegion>
  );
}
