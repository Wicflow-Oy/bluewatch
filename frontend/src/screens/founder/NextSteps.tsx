// What to do next: steps due in the next 30 days, then the steps that have no deadline (investors,
// mostly), kept apart so an open-ended step never reads as due this month. The undated ones are plain
// rows: the ranked list marks its first row as the next step, which an open-ended step never is.
import { CalendarClock } from "lucide-react";
import type { Mode } from "../../api";
import type { NextStep } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText, levelText } from "../../lib/format";
import { stepKindLabel } from "../../lib/labels";
import { KindIcon } from "../../ui/KindIcon";
import { NextStepList } from "../../ui/NextStepList";
import { Panel } from "../../ui/Panel";
import { splitByWindow } from "./deadlines";
import { founderMessages } from "./messages";

const WINDOW_DAYS = 30;

interface NextStepsProps {
  steps: NextStep[];
  mode: Mode;
  today: string;
}

export function NextSteps({ steps, mode, today }: NextStepsProps) {
  const { t, tn } = useT(founderMessages);
  const { dated, undated } = splitByWindow(steps, today, WINDOW_DAYS);
  return (
    <Panel
      className="founder-result__next"
      icon={<CalendarClock size={16} strokeWidth={1.5} aria-hidden="true" />}
      title={t("nextTitle")}
      meta={<span className="mono">{tn("steps", dated.length)}</span>}
    >
      {dated.length > 0 ? (
        <NextStepList steps={dated} mode={mode} today={today} compact />
      ) : (
        <p className="muted">{t("nothingSoon")}</p>
      )}
      {undated.length > 0 && (
        <section className="founder-undated">
          <h3 className="founder-undated__title overline">
            {t("undatedTitle")}
            <span className="mono">{tn("steps", undated.length)}</span>
          </h3>
          <ul className="founder-list">
            {undated.map((step) => (
              <UndatedStep key={`${step.rank}-${step.opportunity_id}`} step={step} mode={mode} />
            ))}
          </ul>
        </section>
      )}
    </Panel>
  );
}

function UndatedStep({ step, mode }: { step: NextStep; mode: Mode }) {
  return (
    <li className="founder-list__row">
      <div className="founder-list__text">
        <span className="founder-list__name">{step.title}</span>
        <span className="founder-list__detail">{levelText(humanText(step.action), mode)}</span>
      </div>
      <span className="founder-undated__kind overline">
        <KindIcon kind={step.kind} />
        {stepKindLabel(step.kind)}
      </span>
    </li>
  );
}
