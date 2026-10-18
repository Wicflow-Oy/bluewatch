// The page header's meta line: how many companies are assessed, and whether they come from recorded data.
// It reads the table's own load; when that fails the table says so, and this line stays empty.
import { use } from "react";
import type { CompanyRow } from "../../contracts";
import { load, type Loaded } from "../../data";
import { useT } from "../../i18n/messages";
import { sourceStateLabel } from "../../lib/labels";
import { usePreset } from "../../lib/preset";
import { useWorkspace } from "../../lib/workspace";
import { companiesMessages } from "./messages";

type CompaniesLoad = Promise<Loaded<CompanyRow[]>>;
const settled = new WeakMap<CompaniesLoad, Promise<Loaded<CompanyRow[]> | null>>();

/** The same promise for the same load, so use() does not suspend again on every render. */
function orNull(loading: CompaniesLoad): Promise<Loaded<CompanyRow[]> | null> {
  let hit = settled.get(loading);
  if (!hit) {
    hit = loading.catch(() => null);
    settled.set(loading, hit);
  }
  return hit;
}

export function CompaniesMeta() {
  const { tn } = useT(companiesMessages);
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const companies = use(orNull(load.companies(mode, preset)));
  if (!companies) return null;
  return (
    <span className="companies-meta">
      <span>{tn("companiesCount", companies.data.length)}</span>
      {companies.origin === "demo" && (
        <>
          <span className="sep-dot" aria-hidden="true" />
          <span>{sourceStateLabel("cached")}</span>
        </>
      )}
    </span>
  );
}
