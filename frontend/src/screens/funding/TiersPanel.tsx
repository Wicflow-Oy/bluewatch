// One company's tiers: the filters, then a group per tier word, or the state that explains an empty list.
import type { Mode } from "../../api";
import { useT } from "../../i18n/messages";
import { formatDay } from "../../lib/format";
import { vars } from "../../lib/motion";
import { useMeta } from "../../lib/meta";
import { uiMessages } from "../../ui/messages";
import { Panel } from "../../ui/Panel";
import { EmptyState } from "../../ui/States";
import { groupByTierWord, TierGroup, type Tier } from "../../ui/TierGroup";
import {
  applyFilters,
  NO_FILTERS,
  type CompanyOption,
  type Filters,
  type FundingItem,
} from "./catalogue";
import { fundingMessages } from "./messages";
import { TierFilters } from "./TierFilters";

/** Long tiers (the possible tier runs to 30 instruments) collapse after this many. */
const COLLAPSED_AFTER = 6;

interface TiersPanelProps {
  company: CompanyOption;
  items: FundingItem[];
  /** The catalogue's own day: deadlines count from it and the panel says the tiers are as of it. */
  today: string;
  mode: Mode;
  filters: Filters;
  onFilters: (filters: Filters) => void;
  /** The instrument id to highlight, from search. */
  focus: string | null;
}

export function TiersPanel({
  company,
  items,
  today,
  mode,
  filters,
  onFilters,
  focus,
}: TiersPanelProps) {
  const { t } = useT(fundingMessages);
  const ui = useT(uiMessages);
  const meta = useMeta();
  const tierWord = (tier: Tier) => meta.tier(tier, mode);
  const shown = applyFilters(items, filters, today, tierWord);
  return (
    <section className="funding__tiers" aria-labelledby="funding-tiers-title">
      <header className="funding__tiers-head">
        <h2 className="t-title" id="funding-tiers-title">
          {t("tiersFor", { company: company.name })}
        </h2>
        <span className="funding__tiers-meta mono">
          {ui.t("asOf", { stamp: formatDay(today, { today: meta.today }) })}
        </span>
      </header>
      {items.length === 0 ? (
        <Panel>
          <EmptyState compact title={t("noFitTitle", { company: company.name })}>
            {t("noFitBody")}
          </EmptyState>
        </Panel>
      ) : (
        <>
          <TierFilters
            items={items}
            shown={shown.length}
            filters={filters}
            onChange={onFilters}
            today={today}
            tierWord={tierWord}
          />
          {shown.length === 0 ? (
            <Panel>
              <NoMatch
                company={company}
                total={items.length}
                onClear={() => onFilters(NO_FILTERS)}
              />
            </Panel>
          ) : (
            groupByTierWord(shown, tierWord).map((group, i) => (
              <div
                key={`${company.id}:${group.tier}`}
                className={`funding__group funding__group--${group.tier} stagger-in`}
                style={vars({ "--i": i })}
              >
                <TierGroup
                  tier={group.tier}
                  mode={mode}
                  items={group.items}
                  collapsedAfter={COLLAPSED_AFTER}
                  highlightId={focus}
                />
              </div>
            ))
          )}
        </>
      )}
    </section>
  );
}

interface NoMatchProps {
  company: CompanyOption;
  total: number;
  onClear: () => void;
}

function NoMatch({ company, total, onClear }: NoMatchProps) {
  const { t, tn } = useT(fundingMessages);
  return (
    <EmptyState
      compact
      title={t("noMatchTitle")}
      action={
        <button type="button" className="btn" onClick={onClear}>
          {t("clearFilters")}
        </button>
      }
    >
      {tn("noMatchBody", total, { company: company.name })}
    </EmptyState>
  );
}
