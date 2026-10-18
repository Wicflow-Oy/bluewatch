// Phones: every filter in one sheet, opened from the "Filters" button.
import { X } from "lucide-react";
import { useT } from "../../i18n/messages";
import { Drawer } from "../../ui/Drawer";
import { OptionList } from "./FacetMenu";
import type { Option } from "./facetOptions";
import { FACETS, type FacetKey, type Selection } from "./filters";
import { companiesMessages } from "./messages";

interface FilterSheetProps {
  open: boolean;
  onClose(): void;
  options(key: FacetKey): Option[];
  selection: Selection;
  onToggle(key: FacetKey, value: string): void;
  /** Present only while a filter is on. */
  onClear?(): void;
}

export function FilterSheet({
  open,
  onClose,
  options,
  selection,
  onToggle,
  onClear,
}: FilterSheetProps) {
  const { t } = useT(companiesMessages);
  return (
    <Drawer open={open} onClose={onClose} label={t("filters")}>
      <div className="filter-sheet">
        <header className="filter-sheet__head">
          <h2 className="filter-sheet__title">{t("filters")}</h2>
          <button
            type="button"
            className="icon-btn"
            aria-label={t("closeFilters")}
            onClick={onClose}
          >
            <X size={16} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </header>
        <div className="filter-sheet__body">
          {FACETS.map((key) => (
            <fieldset key={key} className="filter-sheet__group">
              <legend className="overline">{t(`facet_${key}`)}</legend>
              <OptionList
                options={options(key)}
                isOn={(value) => selection[key].includes(value)}
                onToggle={(value) => onToggle(key, value)}
              />
            </fieldset>
          ))}
        </div>
        <footer className="filter-sheet__foot">
          {onClear && (
            <button type="button" className="btn btn--ghost btn--lg" onClick={onClear}>
              {t("clearFilters")}
            </button>
          )}
          <button type="button" className="btn btn--primary btn--lg" onClick={onClose}>
            {t("showCompanies")}
          </button>
        </footer>
      </div>
    </Drawer>
  );
}
