// The ranked teams. Arrow keys move the selection; each row is a button that opens its plan.
import { useRef, type KeyboardEvent } from "react";
import type { ContactPlan } from "../../contracts";
import { useT } from "../../i18n/messages";
import { floorTo, ofN, trunc } from "../../lib/format";
import { vars } from "../../lib/motion";
import { Chip } from "../../ui/Chip";
import { CompactScoreBar } from "../../ui/ScoreBar";
import { scoutMessages } from "./messages";
import { placementLabel, planFlags, projectTitle, shortEvent } from "./plan";

interface PlanListProps {
  plans: ContactPlan[];
  selectedId: string | null;
  onSelect(id: string): void;
}

export function PlanList({ plans, selectedId, onSelect }: PlanListProps) {
  const { t } = useT(scoutMessages);
  const rows = useRef<(HTMLButtonElement | null)[]>([]);

  const onKeyDown = (e: KeyboardEvent<HTMLOListElement>) => {
    const step = e.key === "ArrowDown" ? 1 : e.key === "ArrowUp" ? -1 : 0;
    if (step === 0) return;
    e.preventDefault();
    const current = plans.findIndex((p) => p.project_id === selectedId);
    const next = Math.min(plans.length - 1, Math.max(0, current + step));
    onSelect(plans[next].project_id);
    rows.current[next]?.focus();
  };

  return (
    <ol className="scout-list" aria-label={t("rankedTeams")} onKeyDown={onKeyDown}>
      {plans.map((plan, i) => (
        <li key={plan.project_id} className="stagger-in" style={vars({ "--i": i })}>
          <button
            type="button"
            ref={(el) => {
              rows.current[i] = el;
            }}
            className="scout-row"
            aria-current={plan.project_id === selectedId ? "true" : undefined}
            onClick={() => onSelect(plan.project_id)}
          >
            <PlanRow plan={plan} rank={i + 1} />
          </button>
        </li>
      ))}
    </ol>
  );
}

function PlanRow({ plan, rank }: { plan: ContactPlan; rank: number }) {
  const { t } = useT(scoutMessages);
  const { total } = plan.promise_score;
  const flags = planFlags(plan);
  const title = projectTitle(plan);
  const meta = [shortEvent(plan), plan.project && placementLabel(plan.project)]
    .filter(Boolean)
    .join(" · ");
  return (
    <>
      <span className="scout-row__rank mono">{String(rank).padStart(2, "0")}</span>
      <span className="scout-row__text">
        <span className="scout-row__title" title={title}>
          {title}
        </span>
        <span className="scout-row__meta" title={meta}>
          {meta}
        </span>
        {flags.length > 0 && (
          <span className="scout-row__flags">
            {flags.map((flag) => (
              <Chip key={flag.kind} tone={flag.tone} title={flag.detail}>
                {flag.label}
              </Chip>
            ))}
          </span>
        )}
      </span>
      <span className="scout-row__score">
        <span className="scout-row__total mono">{trunc(total, 0)}</span>
        <CompactScoreBar
          max={100}
          total={total}
          label={t("promiseScore", { score: ofN(floorTo(total, 0), 100) })}
        />
      </span>
    </>
  );
}
