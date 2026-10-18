// The "wrong company" test: named cases where a careless match picks a namesake. Failures come first
// and open, with what went wrong under the case.
import { Check, ChevronRight, Crosshair, X } from "lucide-react";
import type { TrapResult } from "../../contracts";
import { useT } from "../../i18n/messages";
import { ofN } from "../../lib/format";
import { Chip } from "../../ui/Chip";
import { Panel } from "../../ui/Panel";
import { EmptyState } from "../../ui/States";
import { precisionMessages } from "./messages";
import { failedFirst } from "./model";
import { Figure, Rich } from "./Rich";

export function Traps({ traps }: { traps: TrapResult[] }) {
  const { t } = useT(precisionMessages);
  const passed = traps.filter((trap) => trap.passed).length;
  return (
    <Panel
      title={t("trapsTitle")}
      icon={<Crosshair size={16} strokeWidth={1.5} aria-hidden="true" />}
      meta={
        traps.length > 0 && (
          <Rich
            text={t("trapsPassed")}
            values={{ count: <Figure>{ofN(passed, traps.length)}</Figure> }}
          />
        )
      }
      className="precision__order-2"
    >
      {traps.length > 0 ? (
        <ul className="traps">
          {failedFirst(traps).map((trap) => (
            <li key={trap.case}>
              <TrapRow trap={trap} />
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState compact title={t("noTrapsTitle")}>
          {t("noTrapsBody")}
        </EmptyState>
      )}
    </Panel>
  );
}

function TrapRow({ trap }: { trap: TrapResult }) {
  const { t } = useT(precisionMessages);
  return (
    <details className={`trap inset${trap.passed ? "" : " trap--failed"}`} open={!trap.passed}>
      <summary className="trap__summary">
        <ChevronRight className="trap__chevron" size={14} strokeWidth={1.5} aria-hidden="true" />
        <span className="trap__case">
          {trap.case}
          {!trap.passed && trap.note && <span className="trap__why">{trap.note}</span>}
        </span>
        {trap.passed ? (
          <Chip tone="teal" icon={<Check size={12} strokeWidth={2} aria-hidden="true" />}>
            {t("pass")}
          </Chip>
        ) : (
          <Chip tone="red" icon={<X size={12} strokeWidth={2} aria-hidden="true" />}>
            {t("fail")}
          </Chip>
        )}
      </summary>
      <dl className="trap__detail">
        {trap.passed && trap.note && (
          <div>
            <dt>{t("theTrap")}</dt>
            <dd>{trap.note}</dd>
          </div>
        )}
        <div>
          <dt>{t("expected")}</dt>
          <dd>{trap.expected}</dd>
        </div>
        <div>
          <dt>{t("got")}</dt>
          <dd className="mono">{trap.got}</dd>
        </div>
      </dl>
    </details>
  );
}
