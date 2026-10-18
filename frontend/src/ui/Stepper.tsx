// A short, linear progress line: numbered marks joined by a rule, done steps ticked. On a phone only
// the current step's label shows, so four steps never wrap.
import { Check } from "lucide-react";
import { useT } from "../i18n/messages";
import { uiMessages } from "./messages";
import "./Stepper.css";

export interface StepperStep {
  id: string;
  label: string;
  done: boolean;
}

export function Stepper({ steps, current }: { steps: StepperStep[]; current: string }) {
  const { t } = useT(uiMessages);
  const currentStep = steps.find((s) => s.id === current) ?? steps[0];
  return (
    <div className="stepper">
      <ol className="stepper__list">
        {steps.map((step, i) => {
          const isCurrent = step.id === current;
          const state = step.done ? "done" : isCurrent ? "current" : "todo";
          return (
            <li
              key={step.id}
              className={`stepper__step stepper__step--${state}`}
              aria-current={isCurrent ? "step" : undefined}
            >
              <span className="stepper__mark" aria-hidden="true">
                {step.done ? (
                  <Check size={12} strokeWidth={2.5} />
                ) : (
                  <span className="mono">{i + 1}</span>
                )}
              </span>
              <span className="stepper__label" aria-hidden={step.done}>
                {step.label}
              </span>
              {step.done && <span className="sr-only">{t("stepDone", { step: step.label })}</span>}
            </li>
          );
        })}
      </ol>
      <p className="stepper__current" aria-hidden="true">
        {currentStep?.label}
      </p>
    </div>
  );
}
