// After a second lookup: the calls whose tier differs from the previous company's, with the rule between.
import { ArrowRight, GitCompareArrows } from "lucide-react";
import type { Mode } from "../../api";
import { useT } from "../../i18n/messages";
import { humanText, ofN } from "../../lib/format";
import { TierChip } from "../../ui/Chip";
import { Panel } from "../../ui/Panel";
import { RuleLine } from "../../ui/RuleLine";
import type { Comparison, TierChange } from "./compare";
import { founderMessages } from "./messages";

const SHOWN = 3;

export function CompareStrip({ comparison, mode }: { comparison: Comparison; mode: Mode }) {
  const { t } = useT(founderMessages);
  const { name, country, changes, total } = comparison;
  return (
    <Panel
      className="founder-compare"
      icon={<GitCompareArrows size={16} strokeWidth={1.5} aria-hidden="true" />}
      title={t("comparedWith", { name, country })}
      meta={
        <span className="mono">{t("tiersChanged", { count: ofN(changes.length, total) })}</span>
      }
    >
      {changes.length === 0 ? (
        <p className="muted">{t("noTierChanges")}</p>
      ) : (
        <ul className="founder-compare__list">
          {changes.slice(0, SHOWN).map((change) => (
            <ChangeRow key={change.instrumentId} change={change} mode={mode} />
          ))}
        </ul>
      )}
    </Panel>
  );
}

function ChangeRow({ change, mode }: { change: TierChange; mode: Mode }) {
  const { t } = useT(founderMessages);
  return (
    <li className="founder-compare__item">
      <div className="founder-compare__head">
        <span className="founder-compare__name">{change.name}</span>
        <span className="founder-compare__flip">
          <TierChip tier={change.before} mode={mode} />
          <ArrowRight size={14} strokeWidth={1.5} aria-hidden="true" />
          <span className="sr-only">{t("changesTo")}</span>
          <TierChip tier={change.after} mode={mode} />
        </span>
      </div>
      <RuleLine
        rule={humanText(change.rule)}
        source={change.ruleSource}
        verified={change.ruleVerified}
      />
    </li>
  );
}
