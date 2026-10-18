// The ranked plans read as a pipeline of future founders: from a result on an organiser's page to a team
// that opts in. Every count is taken from the plans on screen.
import { ChevronRight } from "lucide-react";
import type { ContactPlan } from "../../contracts";
import { useT } from "../../i18n/messages";
import { vars } from "../../lib/motion";
import { CountUp } from "../../ui/CountUp";
import { uiMessages } from "../../ui/messages";
import { scoutMessages } from "./messages";

interface Stage {
  label: string;
  /** A count of the plans, or a word where the stage is not a count. */
  value: number | string;
  /** The n a count is out of; absent where the value is not a count of the plans. */
  of?: number;
  caption: string;
}

function useStages(plans: ContactPlan[]): Stage[] {
  const { t } = useT(scoutMessages);
  const n = plans.length;
  const count = (test: (plan: ContactPlan) => boolean) => ({
    value: plans.filter(test).length,
    of: n,
  });
  return [
    { label: t("rankedTeams"), value: n, caption: t("stageRankedCaption") },
    {
      label: t("stageNoCompany"),
      ...count((p) => p.project?.company_status === "none_found"),
      caption: t("stageNoCompanyCaption"),
    },
    {
      label: t("stageOrganisation"),
      ...count((p) => p.draft != null),
      caption: t("stageOrganisationCaption"),
    },
    {
      label: t("stageWarm"),
      ...count((p) => (p.route_ladder ?? []).some((r) => r.kind === "warm_intro")),
      caption: t("stageWarmCaption"),
    },
    { label: "Idea Harbour", value: t("stageOptIn"), caption: t("stageOptInCaption") },
  ];
}

export function Pipeline({ plans }: { plans: ContactPlan[] }) {
  const { t } = useT(scoutMessages);
  const ui = useT(uiMessages);
  const stages = useStages(plans);
  return (
    <ol className="scout-pipeline" aria-label={t("pipelineLabel")}>
      {stages.map((stage, i) => (
        <li key={stage.label} className="scout-stage capsule stagger-in" style={vars({ "--i": i })}>
          {i > 0 && (
            <ChevronRight
              className="scout-stage__chevron"
              size={16}
              strokeWidth={1.75}
              aria-hidden="true"
            />
          )}
          <span className="overline">{stage.label}</span>
          <span className="scout-stage__value">
            {typeof stage.value === "number" ? (
              <span className="t-num-md">
                <CountUp value={stage.value} decimals={0} delay={i * 60} />
              </span>
            ) : (
              <span className="scout-stage__word">{stage.value}</span>
            )}
            {stage.of !== undefined && (
              <span className="scout-stage__of mono">{ui.t("outOf", { n: stage.of })}</span>
            )}
          </span>
          <span className="scout-stage__caption">{stage.caption}</span>
        </li>
      ))}
    </ol>
  );
}
