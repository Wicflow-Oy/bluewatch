import type { Mode } from "../../api";
import type { VentureCard } from "../../contracts";
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import type { CardTab } from "../../lib/router";
import { Panel } from "../../ui/Panel";
import { ReadinessPanel } from "../../ui/ReadinessPanel";
import { cardMessages } from "./messages";
import { NextStepsPanel } from "./NextStepsPanel";
import { ScorePanel } from "./ScorePanel";
import { WhatWeKnow } from "./WhatWeKnow";

interface OverviewTabProps {
  card: VentureCard;
  mode: Mode;
  /** The full page shows the next steps in its right rail instead. */
  withNextSteps: boolean;
  onTabChange(tab: CardTab): void;
}

/** Three columns in the sheet: the two values and readiness, what we know, the next steps in order. */
export function OverviewTab({ card, mode, withNextSteps, onTabChange }: OverviewTabProps) {
  const { t } = useT(cardMessages);
  const meta = useMeta();
  const { assessment } = card;
  return (
    <div className={`overview${withNextSteps ? " overview--steps" : ""}`}>
      <div className="overview__col overview__col--score">
        <ScorePanel score={assessment.score} mode={mode} />
        <Panel
          title={t("readiness")}
          meta={<span className="vc-hint">{t("readinessHint")}</span>}
          className="readiness-card"
        >
          <ReadinessPanel levels={assessment.levels} mode={mode} />
        </Panel>
      </div>
      <div className="overview__col overview__col--know">
        <WhatWeKnow card={card} onOpenEvidence={() => onTabChange("evidence")} />
      </div>
      {withNextSteps && (
        <div className="overview__col overview__col--steps">
          <NextStepsPanel card={card} mode={mode} today={meta.today} />
        </div>
      )}
    </div>
  );
}
