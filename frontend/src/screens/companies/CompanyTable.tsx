// Every assessed company, filterable and sortable. A row opens the company's card in the drawer.
import { use, useMemo, useState } from "react";
import type { CompanyRow } from "../../contracts";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { GROUP_ORDER } from "../../lib/labels";
import { useMeta } from "../../lib/meta";
import { usePreset } from "../../lib/preset";
import { useWorkspace } from "../../lib/workspace";
import { DataTable } from "../../ui/DataTable";
import { companyColumns, StackedRow } from "./columns";
import { FilterBar } from "./FilterBar";
import { applyFilters, NO_SELECTION, selectedCount, type FacetKey } from "./filters";
import { companiesMessages } from "./messages";
import { NoMatch } from "./NoMatch";

/** Group order first (Act now on top), then the biggest potential. */
function defaultOrder(a: CompanyRow, b: CompanyRow): number {
  return (
    GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group) ||
    b.potential - a.potential ||
    b.evidence - a.evidence ||
    a.name.localeCompare(b.name)
  );
}

interface CompanyTableProps {
  selectedId?: string;
  onOpen(companyId: string): void;
  /** Hand a name or ID with no match in the table to "Look up any company". */
  onLookUp(text: string): void;
}

export function CompanyTable({ selectedId, onOpen, onLookUp }: CompanyTableProps) {
  const { t } = useT(companiesMessages);
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const meta = useMeta();
  // Both start before either is awaited, so they load side by side.
  const companiesLoad = load.companies(mode, preset);
  const listLoad = load.list(mode, preset);
  const companies = use(companiesLoad);
  const list = use(listLoad);

  const [text, setText] = useState("");
  const [selection, setSelection] = useState(NO_SELECTION);
  const rows = useMemo(() => [...companies.data].sort(defaultOrder), [companies]);
  const listedIds = useMemo(() => new Set(list.data.entries.map((e) => e.company_id)), [list]);
  const shown = useMemo(
    () => applyFilters(rows, text, selection, listedIds),
    [rows, text, selection, listedIds],
  );
  const columns = useMemo(() => companyColumns(t, meta.today), [t, meta.today]);

  const toggle = (key: FacetKey, value: string) =>
    setSelection((current) => ({
      ...current,
      [key]: current[key].includes(value)
        ? current[key].filter((v) => v !== value)
        : [...current[key], value],
    }));
  const clear = () => {
    setText("");
    setSelection(NO_SELECTION);
  };

  return (
    <section className="company-table" aria-labelledby="company-table-title">
      <header className="company-table__head">
        <h2 className="company-table__title" id="company-table-title">
          {t("tableTitle")}
        </h2>
        <span className="company-table__count">
          {shown.length === rows.length
            ? t("shownAll", { n: rows.length })
            : t("shownSome", { shown: shown.length, total: rows.length })}
        </span>
      </header>
      <FilterBar
        rows={rows}
        listedIds={listedIds}
        text={text}
        onText={setText}
        selection={selection}
        onToggle={toggle}
        onClear={clear}
      />
      {shown.length > 0 ? (
        <DataTable
          rows={shown}
          columns={columns}
          getRowId={(r) => r.id}
          selectedId={selectedId}
          onOpen={(r) => onOpen(r.id)}
          stackedRow={(r) => <StackedRow row={r} />}
          label={t("tableTitle")}
        />
      ) : (
        <NoMatch
          text={text}
          filtered={selectedCount(selection) > 0}
          onClear={clear}
          onLookUp={onLookUp}
        />
      )}
    </section>
  );
}
