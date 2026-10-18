// The table's filters: a text filter, one menu per facet on wider screens, one "Filters" sheet on phones.
// Every option shows how many companies it would leave.
import { ListFilter, Search } from "lucide-react";
import { useState } from "react";
import { useT } from "../../i18n/messages";
import { Toggle } from "../../ui/Toggle";
import { FacetMenu } from "./FacetMenu";
import { useFacetOptions, type FacetInput } from "./facetOptions";
import { FilterSheet } from "./FilterSheet";
import { LISTED, selectedCount, type FacetKey } from "./filters";
import { companiesMessages } from "./messages";

const MENU_FACETS = ["country", "group", "vertical", "match"] as const satisfies FacetKey[];

export interface FilterBarProps extends FacetInput {
  onText(text: string): void;
  onToggle(key: FacetKey, value: string): void;
  onClear(): void;
}

export function FilterBar(props: FilterBarProps) {
  const { text, onText, selection, onToggle, onClear } = props;
  const { t } = useT(companiesMessages);
  const options = useFacetOptions(props);
  const [sheetOpen, setSheetOpen] = useState(false);
  const active = selectedCount(selection);
  const listed = options("listed")[0];

  return (
    <div className="filters">
      <label className="filters__search">
        <Search size={16} strokeWidth={1.5} aria-hidden="true" />
        <span className="sr-only">{t("filterByText")}</span>
        <input
          className="input"
          type="search"
          value={text}
          onChange={(e) => onText(e.target.value)}
          placeholder={t("filterByText")}
          autoComplete="off"
          spellCheck={false}
        />
      </label>
      <div className="filters__menus">
        {MENU_FACETS.map((key) => (
          <FacetMenu
            key={key}
            label={t(`facet_${key}`)}
            selected={selection[key].length}
            options={options(key)}
            isOn={(value) => selection[key].includes(value)}
            onToggle={(value) => onToggle(key, value)}
          />
        ))}
        {listed && (
          <span className="filters__toggle">
            <Toggle
              checked={selection.listed.includes(LISTED)}
              onChange={() => onToggle("listed", LISTED)}
              label={t("onListCount", { n: listed.count })}
            />
          </span>
        )}
        {active > 0 && (
          <button type="button" className="btn btn--ghost btn--sm" onClick={onClear}>
            {t("clearFilters")}
          </button>
        )}
      </div>
      <button
        type="button"
        className="btn filters__sheet-button"
        aria-haspopup="dialog"
        onClick={() => setSheetOpen(true)}
      >
        <ListFilter size={16} strokeWidth={1.5} aria-hidden="true" />
        {t("filters")}
        {active > 0 && <span className="mono"> ({active})</span>}
      </button>
      <FilterSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        options={options}
        selection={selection}
        onToggle={onToggle}
        onClear={active > 0 ? onClear : undefined}
      />
    </div>
  );
}
