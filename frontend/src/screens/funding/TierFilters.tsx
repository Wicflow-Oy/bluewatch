import { useT } from "../../i18n/messages";
import { ofN } from "../../lib/format";
import { STEP_KINDS, stepKindLabel } from "../../lib/labels";
import { tiersByWord, type Tier } from "../../ui/TierGroup";
import {
  inWindow,
  NO_FILTERS,
  type DeadlineWindow,
  type Filters,
  type FundingItem,
} from "./catalogue";
import { FilterSelect, type SelectOption } from "./FilterSelect";
import { fundingMessages } from "./messages";

const WINDOWS: Exclude<DeadlineWindow, "any">[] = ["14", "30", "90"];

interface TierFiltersProps {
  items: FundingItem[];
  shown: number;
  filters: Filters;
  onChange: (filters: Filters) => void;
  today: string;
  tierWord: (tier: Tier) => string;
}

const withCount = (label: string, n: number) => `${label} · ${n}`;

/** Counts are over all of the company's instruments, so an option never hides how many it holds. */
export function TierFilters({
  items,
  shown,
  filters,
  onChange,
  today,
  tierWord,
}: TierFiltersProps) {
  const { t, tn } = useT(fundingMessages);
  const count = (match: (item: FundingItem) => boolean) => items.filter(match).length;

  const kinds = STEP_KINDS.filter((k) => items.some((i) => i.kind === k));
  const kindOptions: SelectOption<Filters["kind"]>[] = [
    { value: "all", label: withCount(t("allKinds"), items.length) },
    ...kinds.map((k) => ({
      value: k,
      label: withCount(
        stepKindLabel(k),
        count((i) => i.kind === k),
      ),
    })),
  ];

  const windowOptions: SelectOption<DeadlineWindow>[] = [
    { value: "any", label: withCount(t("anyDate"), items.length) },
    ...WINDOWS.map((value) => ({
      value,
      label: withCount(
        tn("within", Number(value)),
        count((i) => inWindow(i, value, today)),
      ),
    })),
  ];

  // One option per word, valued by the word's strongest tier: A'Pelago's "Likely" covers two tiers.
  const groups = tiersByWord(tierWord);
  const picked = filters.tier;
  const tierValue =
    picked === "all" ? "all" : (groups.find((tiers) => tiers.includes(picked))?.[0] ?? "all");
  const tierOptions: SelectOption<Filters["tier"]>[] = [
    { value: "all", label: withCount(t("allTiers"), items.length) },
    ...groups.flatMap((tiers): SelectOption<Filters["tier"]>[] => {
      const n = count((i) => tiers.includes(i.tier));
      const tier = tiers[0];
      return n > 0 || tier === tierValue
        ? [{ value: tier, label: withCount(tierWord(tier), n) }]
        : [];
    }),
  ];

  const filtered = filters.kind !== "all" || filters.window !== "any" || filters.tier !== "all";

  return (
    <div className="tier-filters">
      <div className="tier-filters__controls">
        <FilterSelect
          label={t("kind")}
          value={filters.kind}
          options={kindOptions}
          onChange={(kind) => onChange({ ...filters, kind })}
        />
        <FilterSelect
          label={t("deadline")}
          value={filters.window}
          options={windowOptions}
          onChange={(window) => onChange({ ...filters, window })}
        />
        <FilterSelect
          label={t("tier")}
          value={tierValue}
          options={tierOptions}
          onChange={(tier) => onChange({ ...filters, tier })}
        />
      </div>
      <div className="tier-filters__summary">
        <p aria-live="polite">
          {tn("instruments", items.length, { count: ofN(shown, items.length) })}
        </p>
        {/* At zero the empty state below the filters offers the same button. */}
        {filtered && shown > 0 && (
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => onChange(NO_FILTERS)}
          >
            {t("clearFilters")}
          </button>
        )}
      </div>
    </div>
  );
}
