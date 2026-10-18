// The team as the organiser published it: name, event, place and placement (in the interface language), the results page as the
// source, whether a company exists, the idea, and the flags worth acting on.
import { Fragment } from "react";
import type { ContactPlan } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { evidenceSourceLabel } from "../../lib/labels";
import { Chip } from "../../ui/Chip";
import { SourceChip } from "../../ui/SourceChip";
import { scoutMessages } from "./messages";
import {
  placementLabel,
  planFlags,
  projectEvent,
  projectPlace,
  projectTitle,
  STATUS_TONES,
} from "./plan";

const RESULTS_PAGE = { source_family: "hackathon_results" };

export function PlanHeader({ plan, titleId }: { plan: ContactPlan; titleId: string }) {
  const { t } = useT(scoutMessages);
  const project = plan.project;
  const status = project?.company_status ?? "check";
  const flags = planFlags(plan);
  const facts = [
    projectEvent(plan),
    project && projectPlace(project),
    project && placementLabel(project),
  ].filter(Boolean);
  return (
    <header className="scout-detail__header">
      <h2 id={titleId} className="scout-detail__title t-h2">
        {projectTitle(plan)}
      </h2>
      <p className="scout-detail__facts">
        {facts.map((fact, i) => (
          <Fragment key={i}>
            {i > 0 && <span className="sep-dot" aria-hidden="true" />}
            <span>{fact}</span>
          </Fragment>
        ))}
      </p>
      <div className="scout-detail__chips">
        <SourceChip
          source={{
            label: evidenceSourceLabel(RESULTS_PAGE) ?? "",
            url: project?.source_url,
            event: project?.year ? String(project.year) : null,
          }}
        />
        <Chip tone={STATUS_TONES[status]}>{t(`status_${status}`)}</Chip>
      </div>
      {project?.idea && <p className="scout-detail__prose">{humanText(project.idea)}</p>}
      {flags.length > 0 && (
        <ul className="scout-flags">
          {flags.map((flag) => (
            <li key={flag.kind} className="scout-flag">
              <Chip tone={flag.tone} wrap>
                {flag.label}
              </Chip>
              <span className="scout-flag__detail">{flag.detail}</span>
            </li>
          ))}
        </ul>
      )}
    </header>
  );
}
