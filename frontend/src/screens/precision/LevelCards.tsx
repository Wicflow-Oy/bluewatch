// One card per readiness level: how often we land in the answer key's band (or stage) beside the age
// baseline, then within one level, the interval and kappa. A level without answer keys says so instead
// of showing zeros, and a kappa that wasn't computed says why.
import type { LevelAgreement } from "../../contracts";
import { useT } from "../../i18n/messages";
import { ofN, trunc } from "../../lib/format";
import { useMeta } from "../../lib/meta";
import { vars } from "../../lib/motion";
import { wilson } from "../../lib/stats";
import { Chip } from "../../ui/Chip";
import { uiMessages } from "../../ui/messages";
import { Panel } from "../../ui/Panel";
import { StatPair } from "../../ui/StatPair";
import { precisionMessages } from "./messages";
import { agreementUnit } from "./model";
import { Figure } from "./Rich";

export function LevelCards({ levels }: { levels: LevelAgreement[] }) {
  return (
    <div className="precision__levels">
      {levels.map((level, i) => (
        <div key={level.key} className="level-card__slot stagger-in" style={vars({ "--i": i })}>
          {level.n === 0 ? <NoKeysCard level={level} /> : <LevelCard level={level} />}
        </div>
      ))}
    </div>
  );
}

function NoKeysCard({ level }: { level: LevelAgreement }) {
  const { t } = useT(precisionMessages);
  const meta = useMeta();
  return (
    <Panel className="level-card level-card--no-keys">
      <p className="level-card__overline overline">{meta.level(level.key)}</p>
      <p className="level-card__no-keys inset">
        {t("noKeys")} {t(level.key === "oirl" ? "noKeysImpact" : "noKeysOther")}
      </p>
      <p className="level-card__n mono">n = 0</p>
    </Panel>
  );
}

function LevelCard({ level }: { level: LevelAgreement }) {
  const { t } = useT(precisionMessages);
  const ui = useT(uiMessages);
  const meta = useMeta();
  const baselineWithin = level.baseline_within_one;
  const unit = agreementUnit(level.key);
  const kappa = level.weighted_kappa;
  return (
    <Panel className="level-card">
      <StatPair
        label={meta.level(level.key)}
        measure={t(`measure_${unit}`)}
        ours={level.exact}
        baseline={level.baseline_exact ?? null}
        n={level.n}
        interval={wilson(level.exact, level.n)}
      />
      <dl className="level-card__rows">
        <div className="level-card__row">
          <dt>{t(`withinOne_${unit}`)}</dt>
          <dd className="level-card__pair">
            <Figure>{ofN(level.within_one, level.n)}</Figure>
            <span>
              <span className="sr-only">{ui.t("statAgeBaseline")} </span>
              {baselineWithin === null || baselineWithin === undefined ? (
                <Chip tone="hatch">{ui.t("state_unknown")}</Chip>
              ) : (
                <Figure>{ofN(baselineWithin, level.n)}</Figure>
              )}
            </span>
          </dd>
        </div>
        <div className="level-card__row">
          <dt>{t("weightedKappa")}</dt>
          <dd>
            {typeof kappa === "number" && Number.isFinite(kappa) ? (
              <Figure>{trunc(kappa)}</Figure>
            ) : (
              <Chip tone="hatch" wrap>
                {t(level.n < 10 ? "notComputedSmallN" : "notComputed")}
              </Chip>
            )}
          </dd>
        </div>
      </dl>
      <p className="level-card__n mono">n = {level.n}</p>
    </Panel>
  );
}
