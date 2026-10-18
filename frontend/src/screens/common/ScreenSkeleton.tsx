// The calm loading shape every screen starts from: its real title, then shimmering panels. Screens
// replace it with their content; it stays as their Suspense fallback.
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import type { PageName } from "../../lib/router";
import { shellMessages } from "../../shell/messages";
import { NAV, navLabel } from "../../shell/nav";
import { PageHeader, Panel } from "../../ui/Panel";
import { LoadingRegion, Skeleton, SkeletonLines } from "../../ui/States";
import "./ScreenSkeleton.css";

interface ScreenSkeletonProps {
  route: PageName;
  /** A record is open (a company or a bridge): show its detail panel too. */
  detail?: boolean;
}

export function ScreenSkeleton({ route, detail = false }: ScreenSkeletonProps) {
  const { t } = useT(shellMessages);
  const meta = useMeta();
  const item = NAV.find((n) => n.route === route);
  const title = item ? navLabel(item, meta.listName) : meta.productName;
  return (
    <div className="page">
      <PageHeader title={title} />
      <LoadingRegion label={t("loadingPage", { page: title })}>
        <Panel>
          <SkeletonLines lines={5} gap={12} />
        </Panel>
        {detail && <DetailSkeleton />}
      </LoadingRegion>
    </div>
  );
}

/** The venture card's shape: rank tile and name, a meta line, then three column blocks. */
export function DetailSkeleton() {
  return (
    <Panel className="detail-skeleton">
      <div className="detail-skeleton__head">
        <Skeleton width={52} height={52} radius={16} />
        <div className="detail-skeleton__name">
          <Skeleton width={240} height={28} />
          <Skeleton width="60%" />
        </div>
      </div>
      <div className="detail-skeleton__cols">
        <Skeleton height={180} radius={24} />
        <Skeleton height={180} radius={24} />
        <Skeleton height={180} radius={24} />
      </div>
    </Panel>
  );
}
