import { ExternalLink } from "lucide-react";
import { useT } from "../../../i18n/messages";
import { Chip } from "../../../ui/Chip";
import { Deadline } from "../../../ui/Deadline";
import type { IdeaStep } from "../types";
import { useToday } from "./hooks";
import { STEP_ICON } from "./icons";
import { readMessages } from "./messages";
import "./read.css";

/** The next steps as a timeline: what to do, why, and the programme's deadline, status and source. */
export function StepList({ steps }: { steps: IdeaStep[] }) {
  const { t } = useT(readMessages);
  const today = useToday();
  return (
    <ol className="ih-steps">
      {steps.map((step) => {
        const Icon = STEP_ICON[step.kind];
        return (
          <li key={`${step.rank}-${step.title}`} className="ih-step">
            <span className="ih-step__node mono" aria-hidden="true">
              {step.rank}
            </span>
            <div className="ih-step__body">
              <p className="ih-step__title">
                {step.title}
                <Icon size={14} strokeWidth={1.5} aria-hidden="true" />
              </p>
              <p className="ih-step__action">{step.action}</p>
              <p className="ih-step__why">{step.why}</p>
              <div className="ih-step__foot">
                <Deadline date={step.deadline} today={today} />
                {step.status && (
                  <Chip tone="outline" wrap>
                    {step.status}
                  </Chip>
                )}
                {step.source_url && (
                  <a
                    className="ih-link"
                    href={step.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink size={12} strokeWidth={1.5} aria-hidden="true" />
                    {t("source")}
                  </a>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
