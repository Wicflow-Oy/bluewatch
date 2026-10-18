// Funding: every grant and programme tier for one listed company, each with the rule that decides it,
// where that rule was read and the deadline; above it, the SBEP call 4 flip between two countries.
import { Suspense, use, useDeferredValue, useState } from "react";
import type { Mode } from "../../api";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { useFundingFocus } from "../../lib/handoff";
import { useWorkspace } from "../../lib/workspace";
import {
  companiesOf,
  defaultCompanyId,
  itemsFor,
  NO_FILTERS,
  sbepFlip,
  type Filters,
} from "./catalogue";
import { FilterSelect } from "./FilterSelect";
import { FlipPanel } from "./FlipPanel";
import { FundingBoundary, FundingHeader, FundingSkeleton, NoCompanyState } from "./FundingStates";
import { fundingMessages } from "./messages";
import { RulesDisclosure, RulesPanel } from "./TierRules";
import { TiersPanel } from "./TiersPanel";
import "./Funding.css";

export function FundingScreen() {
  const { mode } = useWorkspace();
  // Keeps the current tiers on screen while the other workspace's catalogue loads.
  const shownMode = useDeferredValue(mode);
  // The company and the filters live above the workspace, so switching workspace keeps them.
  const [picked, setPicked] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  // An instrument picked in search arrives once, in memory, and is highlighted in the tiers.
  const focus = useFundingFocus();
  return (
    <div className="page funding">
      <FundingBoundary>
        <Suspense fallback={<FundingSkeleton mode={shownMode} />}>
          <FundingContent
            mode={shownMode}
            picked={picked}
            onPick={setPicked}
            filters={filters}
            onFilters={setFilters}
            focus={focus}
          />
        </Suspense>
      </FundingBoundary>
    </div>
  );
}

interface FundingContentProps {
  mode: Mode;
  picked: string | null;
  onPick: (companyId: string) => void;
  filters: Filters;
  onFilters: (filters: Filters) => void;
  /** The instrument id to highlight, from search. */
  focus: string | null;
}

function FundingContent({ mode, picked, onPick, filters, onFilters, focus }: FundingContentProps) {
  const { t } = useT(fundingMessages);
  const catalogue = use(load.funding(mode)).data;
  const companies = companiesOf(catalogue);
  const defaultId = defaultCompanyId(catalogue, companies);
  // With an instrument to highlight, open on a company that has a tier for it.
  const focused = focus ? catalogue.instruments.find((i) => i.id === focus) : undefined;
  const tiered = (companyId: string) =>
    !focused || (focused.tiers ?? []).some((row) => row.company_id === companyId);
  const company =
    companies.find((c) => c.id === picked) ??
    companies.find((c) => c.id === defaultId && tiered(c.id)) ??
    companies.find((c) => tiered(c.id)) ??
    companies.find((c) => c.id === defaultId) ??
    null;

  if (!company) return <NoCompanyState />;

  return (
    <>
      <FundingHeader
        actions={
          <FilterSelect
            label={t("company")}
            className="funding__picker"
            value={company.id}
            options={companies.map((c) => ({ value: c.id, label: c.name }))}
            onChange={onPick}
          />
        }
      />
      <RulesDisclosure mode={mode} />
      <FlipPanel flip={sbepFlip(catalogue)} mode={mode} />
      <div className="funding__body">
        <TiersPanel
          company={company}
          items={itemsFor(catalogue, company.id)}
          today={catalogue.today}
          mode={mode}
          filters={filters}
          onFilters={onFilters}
          focus={focus}
        />
        <RulesPanel mode={mode} />
      </div>
    </>
  );
}
