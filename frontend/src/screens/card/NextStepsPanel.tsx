import type { Mode } from "../../api";
import type { VentureCard } from "../../contracts";
import { useT } from "../../i18n/messages";
import { NextStepList } from "../../ui/NextStepList";
import { Panel } from "../../ui/Panel";
import { cardMessages } from "./messages";

interface NextStepsPanelProps {
  card: VentureCard;
  mode: Mode;
  today: string;
}

export function NextStepsPanel({ card, mode, today }: NextStepsPanelProps) {
  const { t } = useT(cardMessages);
  const steps = card.next_steps ?? [];
  return (
    <Panel
      title={t("nextStepsInOrder")}
      meta={<span className="mono">{steps.length}</span>}
      className="steps-card"
    >
      <p className="panel-sub">{t("nextStepsSub")}</p>
      <NextStepList steps={steps} card={card} mode={mode} today={today} evidenceTab />
    </Panel>
  );
}
