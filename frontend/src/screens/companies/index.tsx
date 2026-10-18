// Companies: every assessed company in one table, plus a lookup for any other company by name or ID.
import { RefreshCw, TriangleAlert } from "lucide-react";
import { Component, Suspense, useRef, useState, type ReactNode } from "react";
import { useT } from "../../i18n/messages";
import { listRow, morph, sheetPanel } from "../../lib/motion";
import { navigate, navigateNow, type CardTab } from "../../lib/router";
import { shellMessages } from "../../shell/messages";
import { Drawer } from "../../ui/Drawer";
import { PageHeader } from "../../ui/Panel";
import { ErrorState } from "../../ui/States";
import { VentureCardView } from "../card";
import { CompanyTable } from "./CompanyTable";
import { CompaniesMeta } from "./CompaniesMeta";
import { CompanyTableSkeleton } from "./CompanyTableSkeleton";
import { LookupPanel } from "./LookupPanel";
import { companiesMessages } from "./messages";
import { useLookup } from "./useLookup";
import "./Companies.css";

export interface CompaniesScreenProps {
  /** The company whose card is open in the drawer. */
  companyId?: string;
  tab?: CardTab;
}

export function CompaniesScreen({ companyId, tab }: CompaniesScreenProps) {
  const { t } = useT(companiesMessages);
  const shell = useT(shellMessages);
  const lookup = useLookup();
  const lookupRef = useRef<HTMLDivElement>(null);
  // The drawer keeps showing the last company while it slides closed.
  const [shownId, setShownId] = useState(companyId);
  if (companyId && companyId !== shownId) setShownId(companyId);

  // The sheet shrinks back into its row; without the View Transitions API it just fades.
  const close = () =>
    morph(
      "bw-card",
      sheetPanel(),
      () => navigateNow({ name: "companies" }),
      () => (shownId ? listRow(shownId) : null),
    );
  const open = (id: string) =>
    morph(
      "bw-card",
      listRow(id),
      () => navigateNow({ name: "companies", companyId: id }),
      sheetPanel,
    );

  const lookUp = (text: string) => {
    lookup.lookUp(text);
    lookupRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="page companies-page">
      <PageHeader
        title={shell.t("page_companies")}
        meta={
          <Suspense fallback={null}>
            <CompaniesMeta />
          </Suspense>
        }
        explainer={t("explainer")}
      />
      <div ref={lookupRef} className="companies-page__lookup">
        <LookupPanel lookup={lookup} />
      </div>
      <ListBoundary>
        <Suspense fallback={<CompanyTableSkeleton />}>
          <CompanyTable selectedId={companyId} onOpen={open} onLookUp={lookUp} />
        </Suspense>
      </ListBoundary>
      <Drawer
        open={companyId !== undefined}
        onClose={close}
        label={t("ventureCard")}
        variant="card"
      >
        {shownId && (
          <VentureCardView
            companyId={shownId}
            tab={tab ?? "overview"}
            layout="drawer"
            onTabChange={(next) => navigate({ name: "companies", companyId: shownId, tab: next })}
            onClose={close}
          />
        )}
      </Drawer>
    </div>
  );
}

/** The table can fail on its own; the lookup above it keeps working. */
class ListBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? <ListFailed /> : this.props.children;
  }
}

function ListFailed() {
  const { t } = useT(companiesMessages);
  return (
    <ErrorState
      icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
      title={t("listFailedTitle")}
      action={
        <button type="button" className="btn" onClick={() => window.location.reload()}>
          <RefreshCw size={14} strokeWidth={1.5} aria-hidden="true" />
          {t("tryAgain")}
        </button>
      }
    >
      {t("listFailedBody")}
    </ErrorState>
  );
}
