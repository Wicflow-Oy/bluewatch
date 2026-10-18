// Every grant and programme the rules checked, grouped by tier, with the country-decided call pinned to
// the top of its own group.
import { Landmark } from "lucide-react";
import type { Mode } from "../../api";
import type { FounderTier } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { TierChip } from "../../ui/Chip";
import { Panel } from "../../ui/Panel";
import { useMeta } from "../../lib/meta";
import { groupByTierWord, TierGroup, type Tier, type TierItem } from "../../ui/TierGroup";
import { soonestFirst } from "./deadlines";
import { founderMessages } from "./messages";

/** Unknown and excluded start collapsed, so the list leads with what is open. */
const COLLAPSED_AFTER: Partial<Record<Tier, number>> = { possible: 6, unknown: 0, excluded: 0 };

// SBEP call 4 is the call where the registration country alone decides the tier (no Finnish funder).
const COUNTRY_DECIDED = /sbep/i;

function toItem(tier: FounderTier, pinnedLabel: string | null): TierItem {
  return {
    pinnedLabel,
    id: tier.instrument_id,
    name: tier.instrument_name,
    tier: tier.tier,
    rule: humanText(tier.deciding_rule),
    ruleSource: tier.rule_source,
    ruleVerified: tier.rule_verified ?? false,
    deadline: tier.deadline,
    upgradePath: tier.upgrade_path ? humanText(tier.upgrade_path) : null,
    unknownReason: tier.unknown_reason ? humanText(tier.unknown_reason) : null,
  };
}

/** The group's order: the country-decided call first, then soonest deadline first among the possible. */
function ordered(group: { tier: Tier; items: FounderTier[] }): FounderTier[] {
  const items = group.tier === "possible" ? [...group.items].sort(soonestFirst) : group.items;
  const pinned = (tier: FounderTier) => (COUNTRY_DECIDED.test(tier.instrument_id) ? 0 : 1);
  return [...items].sort((a, b) => pinned(a) - pinned(b));
}

interface FundingTiersProps {
  tiers: FounderTier[];
  mode: Mode;
  /** The company has a card: the tiers read its researched facts, not the register alone. */
  researched: boolean;
}

export function FundingTiers({ tiers, mode, researched }: FundingTiersProps) {
  const { t, tn } = useT(founderMessages);
  const meta = useMeta();
  // One group per tier word: A'Pelago words certain and likely the same, so they share a group there.
  const groups = groupByTierWord(tiers, (tier) => meta.tier(tier, mode));
  const label = (tier: FounderTier) =>
    COUNTRY_DECIDED.test(tier.instrument_id) ? t("countryDecided") : null;

  return (
    <Panel
      className="founder-result__tiers"
      icon={<Landmark size={16} strokeWidth={1.5} aria-hidden="true" />}
      title={t("tiersTitle")}
      meta={<span className="mono">{tn("calls", tiers.length)}</span>}
    >
      {tiers.length === 0 ? (
        <p className="muted">{t("noTiers")}</p>
      ) : (
        <div className="founder-tiers">
          <ul className="founder-tiers__counts" aria-label={t("callsPerTier")}>
            {groups.map((group) => (
              <li key={group.tier} className="founder-tiers__count">
                <TierChip tier={group.tier} mode={mode} />
                <span className="mono">{group.items.length}</span>
              </li>
            ))}
          </ul>
          {researched && <p className="muted founder-tiers__basis">{t("researchedBasis")}</p>}
          {groups.map((group) => {
            const items = ordered(group).map((tier) => toItem(tier, label(tier)));
            const limit = COLLAPSED_AFTER[group.tier];
            return (
              <TierGroup
                key={group.tier}
                tier={group.tier}
                mode={mode}
                items={items}
                // A pinned call stays in view even in a group that starts collapsed.
                collapsedAfter={
                  limit === undefined ? undefined : limit + (items[0]?.pinnedLabel ? 1 : 0)
                }
              />
            );
          })}
        </div>
      )}
    </Panel>
  );
}
