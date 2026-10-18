import { SlidersHorizontal } from "lucide-react";
import { useT } from "../../i18n/messages";
import { ofN } from "../../lib/format";
import {
  activeCount,
  FACET_KEYS,
  NO_FILTERS,
  type FacetCounts,
  type FacetKey,
  type Filters,
} from "./filters";
import { ideasMessages } from "./messages";
import { readMessages } from "./read/messages";
import { withSlots } from "./read/slots";
import type { Need, OriginKind, Tier } from "./types";

interface FilterBarProps {
  counts: FacetCounts;
  filters: Filters;
  onChange: (filters: Filters) => void;
  shown: number;
  total: number;
  /** Phones fold the groups away behind one disclosure. */
  folded: boolean;
}

export function FilterBar({ counts, filters, onChange, shown, total, folded }: FilterBarProps) {
  const { t } = useT(ideasMessages);
  const active = activeCount(filters);
  const toggle = (key: FacetKey, value: string) => {
    const list = filters[key];
    onChange({
      ...filters,
      [key]: list.includes(value) ? list.filter((v) => v !== value) : [...list, value],
    });
  };

  const groups = FACET_KEYS.filter((key) => counts[key].length > 0).map((key) => (
    <div key={key} className="ih-filter" role="group" aria-label={t(`facet_${key}`)}>
      <span className="overline">{t(`facet_${key}`)}</span>
      <div className="ih-filter__chips">
        {counts[key].map(([value, count]) => (
          <button
            key={value}
            type="button"
            className="chip-btn ih-filter-chip"
            aria-pressed={filters[key].includes(value)}
            onClick={() => toggle(key, value)}
          >
            <FacetLabel facet={key} value={value} />
            <span className="ct">{count}</span>
          </button>
        ))}
      </div>
    </div>
  ));

  const status = active > 0 && (
    <p className="ih-filters__status">
      <span>
        {withSlots(t("showing"), { count: <span className="mono">{ofN(shown, total)}</span> })}
      </span>
      <button
        type="button"
        className="btn btn--subtle btn--sm"
        onClick={() => onChange(NO_FILTERS)}
      >
        {t("clearFilters")}
      </button>
    </p>
  );

  if (folded) {
    return (
      <div className="ih-filters">
        <details className="ih-filters__fold">
          <summary className="btn">
            <SlidersHorizontal aria-hidden="true" />
            {t("filters")}
            {active > 0 && <span className="ih-count">{active}</span>}
          </summary>
          <div className="ih-filters__groups">{groups}</div>
        </details>
        {status}
      </div>
    );
  }
  return (
    <div className="ih-filters">
      <div className="ih-filters__groups">{groups}</div>
      {status}
    </div>
  );
}

/** Enum values get our words; stages and impact areas arrive already worded by the API. */
function FacetLabel({ facet, value }: { facet: FacetKey; value: string }) {
  const { t } = useT(ideasMessages);
  const read = useT(readMessages);
  switch (facet) {
    case "source":
      return t(`sourceFacet_${value as OriginKind}`);
    case "tier":
      return read.t(`tierShort_${value as Tier}`);
    case "need":
      return t(`need_${value as Need}`);
    default:
      return value;
  }
}
