// An empty table: a typed name or ID with no assessed match goes on to the registers; filters that
// leave nothing can be cleared.
import { useT } from "../../i18n/messages";
import { EmptyState } from "../../ui/States";
import { companiesMessages } from "./messages";
import { MIN_NAME_LENGTH } from "./query";

interface NoMatchProps {
  text: string;
  filtered: boolean;
  onClear(): void;
  onLookUp(text: string): void;
}

export function NoMatch({ text, filtered, onClear, onLookUp }: NoMatchProps) {
  const { t } = useT(companiesMessages);
  const typed = text.trim();
  if (typed.length >= MIN_NAME_LENGTH && !filtered)
    return (
      <div className="company-table__empty">
        <EmptyState
          compact
          title={t("noTextMatchTitle", { query: typed })}
          action={
            <button type="button" className="btn btn--primary" onClick={() => onLookUp(typed)}>
              {t("lookUpInRegisters")}
            </button>
          }
        >
          {t("noTextMatchBody")}
        </EmptyState>
      </div>
    );
  return (
    <div className="company-table__empty">
      <EmptyState
        compact
        title={t("noFilterMatchTitle")}
        action={
          <button type="button" className="btn" onClick={onClear}>
            {t("clearFilters")}
          </button>
        }
      >
        {t("noFilterMatchBody")}
      </EmptyState>
    </div>
  );
}
