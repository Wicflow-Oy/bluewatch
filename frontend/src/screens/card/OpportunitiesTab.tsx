import { Compass, Hourglass } from "lucide-react";
import type { Mode } from "../../api";
import type { Opportunity, VentureCard } from "../../contracts";
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import { Panel } from "../../ui/Panel";
import { EmptyState } from "../../ui/States";
import { groupByTierWord, TierGroup, type TierItem } from "../../ui/TierGroup";
import { CounterpartList } from "./CounterpartList";
import { InvestorList } from "./InvestorList";
import { cardMessages } from "./messages";

const FUNDING_KINDS = new Set<Opportunity["kind"]>(["grant", "programme", "pilot"]);
const COUNTERPART_KINDS = new Set<Opportunity["kind"]>(["buyer", "partner"]);

function tierItem(o: Opportunity): TierItem {
  return {
    id: o.id,
    name: o.title,
    tier: o.tier ?? "unknown",
    rule: o.rule ?? "",
    ruleSource: o.rule_source,
    ruleVerified: o.rule_verified ?? false,
    deadline: o.deadline,
    upgradePath: o.upgrade_path,
  };
}

/** Why no funding or investor applies to a company past the stage window: the rule every one of them carries
 * ("Past the stage window: registered 2012 (PRH), over 10 years ago"). Null while the window is open. */
function pastWindow(card: VentureCard): string | null {
  if (!card.assessment.flags?.includes("too_late")) return null;
  const funding = card.opportunities?.find((o) => FUNDING_KINDS.has(o.kind));
  return funding?.rule || card.investors?.[0]?.fit_label || null;
}

/** The tab's count: what the tab lists, so a company past the stage window counts its counterparts only. */
export function opportunityCount(card: VentureCard): number {
  const opportunities = card.opportunities ?? [];
  if (!pastWindow(card)) return opportunities.length + (card.investors?.length ?? 0);
  return opportunities.filter((o) => COUNTERPART_KINDS.has(o.kind)).length;
}

interface OpportunitiesTabProps {
  card: VentureCard;
  mode: Mode;
  today: string;
}

export function OpportunitiesTab({ card, mode, today }: OpportunitiesTabProps) {
  const { t } = useT(cardMessages);
  const meta = useMeta();
  const opportunities = card.opportunities ?? [];
  const funding = opportunities.filter((o) => FUNDING_KINDS.has(o.kind));
  const counterparts = opportunities.filter((o) => COUNTERPART_KINDS.has(o.kind));
  const investors = card.investors ?? [];
  const bridges = card.bridges ?? [];

  if (funding.length + counterparts.length + investors.length + bridges.length === 0) {
    return (
      <EmptyState
        compact
        icon={<Compass size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("noOpportunitiesTitle")}
      >
        {t("noOpportunitiesBody")}
      </EmptyState>
    );
  }

  const late = pastWindow(card);
  const groups = late
    ? []
    : groupByTierWord(funding.map(tierItem), (tier) => meta.tier(tier, mode));
  return (
    <div className="card-stack">
      {late && (
        <p className="callout callout--amber">
          <Hourglass aria-hidden="true" />
          {late}
        </p>
      )}
      {groups.length > 0 && (
        <Panel
          title={t("fundingAndProgrammes")}
          meta={<span className="mono">{funding.length}</span>}
        >
          <div className="tier-groups">
            {groups.map((g) => (
              <TierGroup
                key={g.tier}
                tier={g.tier}
                mode={mode}
                items={g.items}
                collapsedAfter={4}
              />
            ))}
          </div>
        </Panel>
      )}
      {!late && investors.length > 0 && (
        <Panel title={t("investors")} meta={<span className="mono">{investors.length}</span>}>
          <InvestorList investors={investors} />
        </Panel>
      )}
      {bridges.length + counterparts.length > 0 && (
        <Panel
          title={t("counterparts")}
          meta={<span className="mono">{bridges.length + counterparts.length}</span>}
        >
          <CounterpartList bridges={bridges} counterparts={counterparts} today={today} />
        </Panel>
      )}
    </div>
  );
}
