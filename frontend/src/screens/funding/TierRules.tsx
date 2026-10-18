import { ChevronDown, Info } from "lucide-react";
import type { Mode } from "../../api";
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import { TierChip } from "../../ui/Chip";
import { Panel } from "../../ui/Panel";
import { tiersByWord, useTierMeaning } from "../../ui/TierGroup";
import { fundingMessages } from "./messages";

/** Beside the tiers on a wide screen. */
export function RulesPanel({ mode }: { mode: Mode }) {
  const { t } = useT(fundingMessages);
  return (
    <Panel title={t("rulesTitle")} className="funding__rules-panel">
      <TierRules mode={mode} />
    </Panel>
  );
}

/** Above everything on a narrower screen, closed until asked for. */
export function RulesDisclosure({ mode }: { mode: Mode }) {
  const { t } = useT(fundingMessages);
  return (
    <details className="funding__rules-disclosure">
      <summary>
        {t("rulesTitle")}
        <ChevronDown size={16} strokeWidth={1.5} aria-hidden="true" />
      </summary>
      <TierRules mode={mode} />
    </details>
  );
}

/** One row per tier word, the same grouping the tier list uses. */
function TierRules({ mode }: { mode: Mode }) {
  const { t } = useT(fundingMessages);
  const meta = useMeta();
  const meaning = useTierMeaning();
  return (
    <div className="tier-rules">
      <dl className="tier-rules__list">
        {tiersByWord((tier) => meta.tier(tier, mode)).map((tiers) => (
          <div className="tier-rules__row" key={tiers[0]}>
            <dt>
              <TierChip tier={tiers[0]} mode={mode} />
            </dt>
            <dd>{meaning(tiers)}</dd>
          </div>
        ))}
      </dl>
      <p className="tier-rules__note">
        <Info size={14} strokeWidth={1.5} aria-hidden="true" />
        <span>{t("rulesNote")}</span>
      </p>
    </div>
  );
}
