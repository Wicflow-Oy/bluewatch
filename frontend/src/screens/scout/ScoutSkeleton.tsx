// The scout's loading shape: the pipeline, eight list rows and the detail panel, where they will appear.
import { useT } from "../../i18n/messages";
import { shellMessages } from "../../shell/messages";
import { Panel } from "../../ui/Panel";
import { LoadingRegion, Skeleton } from "../../ui/States";
import { DetailSkeleton } from "../common/ScreenSkeleton";
import { scoutMessages } from "./messages";

export function ScoutSkeleton() {
  const { t } = useT(scoutMessages);
  const shell = useT(shellMessages);
  return (
    <LoadingRegion label={shell.t("loadingProduct", { product: shell.t("page_scout") })}>
      <div className="scout-pipeline">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="scout-stage capsule">
            <Skeleton width="60%" />
            <Skeleton width={48} height={22} />
            <Skeleton width="80%" />
          </div>
        ))}
      </div>
      <div className="scout__board">
        <Panel className="scout__list" title={t("rankedTeams")} flush>
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} className="scout-row scout-row--skeleton">
              <Skeleton width={28} height={28} radius={10} />
              <span className="scout-row__text">
                <Skeleton width="70%" height={14} />
                <Skeleton width="45%" />
              </span>
              <Skeleton width={64} height={20} />
            </div>
          ))}
        </Panel>
        <div className="scout__detail">
          <DetailSkeleton />
        </div>
      </div>
    </LoadingRegion>
  );
}
