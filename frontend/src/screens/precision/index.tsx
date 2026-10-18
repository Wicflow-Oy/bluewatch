// Precision: how often our rules agree with an answer key, next to a baseline that only knows each
// company's age. Every figure on this page is read from the PrecisionReport, never written here.
import { RefreshCw, TriangleAlert } from "lucide-react";
import { Suspense, use, useState, type ReactNode } from "react";
import type { PrecisionReport } from "../../contracts";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { shellMessages } from "../../shell/messages";
import { Boundary } from "../../ui/Boundary";
import { PageHeader, Panel } from "../../ui/Panel";
import { ErrorState, LoadingRegion, Skeleton, SkeletonLines } from "../../ui/States";
import { BlindResult } from "./BlindResult";
import { BlindSet } from "./BlindSet";
import { Disagreement } from "./Disagreement";
import { HeaderChips } from "./HeaderChips";
import { Headline } from "./Headline";
import { LevelCards } from "./LevelCards";
import { precisionMessages } from "./messages";
import { Method } from "./Method";
import { orderedLevels } from "./model";
import { Traps } from "./Traps";
import "./Precision.css";

export function PrecisionScreen() {
  return (
    <div className="page precision">
      <Boundary fallback={<Unavailable />}>
        <Suspense fallback={<PrecisionSkeleton />}>
          <PrecisionReportView />
        </Suspense>
      </Boundary>
    </div>
  );
}

function PrecisionReportView() {
  const { data: report, origin } = use(load.precision());
  const apelagoLabels = use(load.meta()).data.level_labels.apelago;
  // A partner's scored file lives in this component's memory only: gone on reload or navigation.
  const [blind, setBlind] = useState<PrecisionReport | null>(null);
  const levels = orderedLevels(report);

  return (
    <>
      <Header actions={<HeaderChips report={report} />} />
      <div className="precision__grid">
        <Headline
          levels={levels}
          apelagoLabel={(key) => apelagoLabels[key] ?? key}
          generatedAt={report.generated_at}
          recorded={origin === "demo"}
        />
        <LevelCards levels={levels} />
        <div className="precision__column precision__column--wide">
          <Disagreement levels={levels} />
          <BlindSet available={origin === "live"} onResult={setBlind} />
        </div>
        <div className="precision__column precision__column--narrow">
          <Traps traps={report.traps ?? []} />
          <Method notes={report.notes ?? []} />
        </div>
        {blind && <BlindResult report={blind} onClear={() => setBlind(null)} />}
      </div>
    </>
  );
}

function Header({ actions }: { actions?: ReactNode }) {
  const shell = useT(shellMessages);
  const { t } = useT(precisionMessages);
  return (
    <PageHeader title={shell.t("page_precision")} explainer={t("explainer")} actions={actions} />
  );
}

function PrecisionSkeleton() {
  const { t } = useT(precisionMessages);
  return (
    <>
      <Header />
      <LoadingRegion label={t("loading")}>
        <div className="precision__grid">
          <Panel title={t("headlineTitle")} className="precision__full">
            <SkeletonLines lines={2} gap={12} />
          </Panel>
          <div className="precision__levels">
            {Array.from({ length: 4 }, (_, i) => (
              <Panel key={i}>
                <Skeleton width="48%" />
                <Skeleton height={32} style={{ marginTop: 16 }} />
                <SkeletonLines lines={3} gap={12} />
              </Panel>
            ))}
          </div>
        </div>
      </LoadingRegion>
    </>
  );
}

function Unavailable() {
  const { t } = useT(precisionMessages);
  return (
    <>
      <Header />
      <div className="precision__unavailable hatch-frame">
        <ErrorState
          compact
          icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
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
      </div>
    </>
  );
}
