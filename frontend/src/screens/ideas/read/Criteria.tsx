// The rubric, criterion by criterion: one row per criterion with the rung reached as three dots (hatched
// when not stated). A row opens to the rung's words, the quote that earned it, the rule and the weight.
import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";
import { useT } from "../../../i18n/messages";
import type { CriterionResult } from "../types";
import { readMessages } from "./messages";
import "./read.css";

const AXES = ["potential", "evidence"] as const;

export function CriteriaList({ criteria }: { criteria: CriterionResult[] }) {
  const { t } = useT(readMessages);
  return (
    <div className="ih-criteria">
      {AXES.map((axis) => (
        <section key={axis} className={`ih-criteria__axis ih-criteria__axis--${axis}`}>
          <h4 className="ih-criteria__head">
            <i aria-hidden="true" />
            {t(axis)}
          </h4>
          <ul>
            {criteria
              .filter((c) => c.axis === axis)
              .map((c) => (
                <li key={c.id}>
                  <Criterion criterion={c} />
                </li>
              ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function Criterion({ criterion: c }: { criterion: CriterionResult }) {
  const { t } = useT(readMessages);
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <>
      <button
        type="button"
        className="ih-crit"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="ih-crit__label">
          {c.label}
          <span className="sr-only">: {c.rung_label}</span>
        </span>
        <RungDots rung={c.rung} />
        <ChevronDown className="ih-crit__chev" size={14} strokeWidth={1.75} aria-hidden="true" />
      </button>
      <div className="ih-crit__more" id={panelId} inert={!open}>
        <div>
          <div className="ih-crit__in">
            <p className="ih-crit__rung mono">
              {c.rung === null ? c.rung_label : `${t("rungOf", { n: c.rung })} · ${c.rung_label}`}
            </p>
            {c.quote && <q className="ih-quote">{c.quote}</q>}
            <p className="ih-crit__rule">{c.rule}</p>
            <p className="ih-crit__weight mono">{t("weight", { weight: c.weight })}</p>
          </div>
        </div>
      </div>
    </>
  );
}

/** Three short bars; a criterion nobody answered is hatched, not empty. */
function RungDots({ rung }: { rung: number | null }) {
  return (
    <span className={`ih-dots${rung === null ? " ih-dots--unknown" : ""}`} aria-hidden="true">
      {[1, 2, 3].map((n) => (
        <i key={n} className={rung !== null && n <= rung ? "is-on" : undefined} />
      ))}
    </span>
  );
}
