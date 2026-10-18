// Which funding tiers changed between two lookups: the "Excluded → Possible" comparison strip.
import type { FounderTier } from "../../contracts";
import { soonestFirst } from "./deadlines";

type Tier = FounderTier["tier"];

const STRENGTH: Record<Tier, number> = {
  excluded: 0,
  unknown: 1,
  possible: 2,
  likely: 3,
  certain: 4,
};

export interface TierChange {
  instrumentId: string;
  name: string;
  before: Tier;
  after: Tier;
  deadline: string | null;
  /** The rule on the weaker side: the one that stands between the two companies. */
  rule: string;
  ruleSource: string | null;
  ruleVerified: boolean;
}

/** The comparison strip: how the new lookup's tiers differ from the previous company's. */
export interface Comparison {
  /** The previous company, as the register names it. */
  name: string;
  country: string;
  changes: TierChange[];
  /** How many calls the new lookup was checked against. */
  total: number;
}

const opened = (c: TierChange) => (STRENGTH[c.after] > STRENGTH[c.before] ? 1 : 0);

/** Calls that opened up for the new company come first, each group by deadline. */
export function tierChanges(before: FounderTier[], after: FounderTier[]): TierChange[] {
  const previous = new Map(before.map((t) => [t.instrument_id, t]));
  return after
    .flatMap((next): TierChange[] => {
      const prev = previous.get(next.instrument_id);
      if (!prev || prev.tier === next.tier) return [];
      const weaker = STRENGTH[prev.tier] < STRENGTH[next.tier] ? prev : next;
      return [
        {
          instrumentId: next.instrument_id,
          name: next.instrument_name,
          before: prev.tier,
          after: next.tier,
          deadline: next.deadline ?? null,
          rule: weaker.deciding_rule,
          ruleSource: weaker.rule_source ?? null,
          ruleVerified: weaker.rule_verified ?? false,
        },
      ];
    })
    .sort((a, b) => opened(b) - opened(a) || soonestFirst(a, b));
}
