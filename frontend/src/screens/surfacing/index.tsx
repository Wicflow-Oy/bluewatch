// Now Surfacing: the always-on shortlist of who is worth a look now, why, and the next step.
import { RefreshCw, TriangleAlert } from "lucide-react";
import { Suspense } from "react";
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import { usePreset } from "../../lib/preset";
import type { CardTab } from "../../lib/router";
import { IS_MAC } from "../../shell/TopBar";
import { Boundary } from "../../ui/Boundary";
import { PageHeader } from "../../ui/Panel";
import { ErrorState } from "../../ui/States";
import { surfacingMessages } from "./messages";
import { Shortlist } from "./Shortlist";
import { SurfacingSkeleton } from "./SurfacingSkeleton";

import "./Surfacing.css";

export interface SurfacingScreenProps {
  /** The company whose card is open in the sheet. */
  companyId?: string;
  tab?: CardTab;
}

export function SurfacingScreen({ companyId, tab }: SurfacingScreenProps) {
  const meta = useMeta();
  const { preset } = usePreset();
  return (
    <div className="page surfacing">
      {/* A new workspace or preset is a new request, so a failed one is retried by switching. */}
      <Boundary key={`${meta.mode}:${preset}`} fallback={<ListError title={meta.listName} />}>
        <Suspense fallback={<SurfacingSkeleton title={meta.listName} />}>
          <Shortlist companyId={companyId} tab={tab} />
        </Suspense>
      </Boundary>
    </div>
  );
}

function ListError({ title }: { title: string }) {
  const { t } = useT(surfacingMessages);
  return (
    <>
      <PageHeader title={title} />
      <ErrorState
        icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("listFailedTitle")}
        action={
          <button type="button" className="btn" onClick={() => window.location.reload()}>
            <RefreshCw size={14} strokeWidth={1.5} aria-hidden="true" />
            {t("retry")}
          </button>
        }
      >
        {t("listFailedBody", { keys: IS_MAC ? "⌘K" : "Ctrl K" })}
      </ErrorState>
    </>
  );
}
