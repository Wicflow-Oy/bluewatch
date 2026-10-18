// One screen per route. Each screen lives in its own folder, owns everything below its props, and is
// its own chunk: the first paint downloads only the page it lands on.
import { Compass } from "lucide-react";
import { lazy, Suspense } from "react";
import type { Mode } from "../api";
import { load } from "../data";
import { useT } from "../i18n/messages";
import { useMeta } from "../lib/meta";
import type { PresetName } from "../lib/preset";
import { isStandalone, navigate, pageOf, type Route, type StandaloneRoute } from "../lib/router";
import { BootScreen } from "../shell/BootScreen";
import { shellMessages } from "../shell/messages";
import { usePageTitle } from "../shell/usePageTitle";
import { EmptyState } from "../ui/States";
import { ScreenSkeleton } from "./common/ScreenSkeleton";

// Each screen's chunk, shared by lazy() and the boot preload so both ask for the same module.
const chunks = {
  surfacing: () => import("./surfacing"),
  companies: () => import("./companies"),
  card: () => import("./card"),
  bridges: () => import("./bridges"),
  funding: () => import("./funding"),
  founder: () => import("./founder"),
  scout: () => import("./scout"),
  outreach: () => import("./outreach"),
  precision: () => import("./precision"),
  ideas: () => import("./ideas"),
  apply: () => import("./apply"),
  guide: () => import("./guide"),
};

const SurfacingScreen = lazy(() =>
  chunks.surfacing().then((m) => ({ default: m.SurfacingScreen })),
);
const CompaniesScreen = lazy(() =>
  chunks.companies().then((m) => ({ default: m.CompaniesScreen })),
);
const VentureCardView = lazy(() => chunks.card().then((m) => ({ default: m.VentureCardView })));
const BridgesScreen = lazy(() => chunks.bridges().then((m) => ({ default: m.BridgesScreen })));
const FundingScreen = lazy(() => chunks.funding().then((m) => ({ default: m.FundingScreen })));
const FounderScreen = lazy(() => chunks.founder().then((m) => ({ default: m.FounderScreen })));
const ScoutScreen = lazy(() => chunks.scout().then((m) => ({ default: m.ScoutScreen })));
const OutreachScreen = lazy(() => chunks.outreach().then((m) => ({ default: m.OutreachScreen })));
const PrecisionScreen = lazy(() =>
  chunks.precision().then((m) => ({ default: m.PrecisionScreen })),
);
const IdeasScreen = lazy(() => chunks.ideas().then((m) => ({ default: m.IdeasScreen })));
const ApplyScreen = lazy(() => chunks.apply().then((m) => ({ default: m.ApplyScreen })));
const GuideScreen = lazy(() => chunks.guide().then((m) => ({ default: m.GuideScreen })));

/** Starts the landing route's chunk and the data its first screen reads, so both are in flight while
 * the boot screen waits for /api/meta. The screens read the same memoised loads, so nothing runs twice;
 * a failure surfaces where the screen reads it, not here. */
export function preloadRoute(route: Route, mode: Mode, preset: PresetName): void {
  if (isStandalone(route) || route.name === "not_found") return;
  // The top bar reads the list and the alerts on every page.
  const pending: Promise<unknown>[] = [
    chunks[route.name](),
    load.list(mode, preset),
    load.alerts(mode),
  ];
  const companyId = "companyId" in route ? route.companyId : undefined;
  if (companyId) pending.push(chunks.card(), load.card(companyId, mode, preset));
  switch (route.name) {
    case "companies":
    case "outreach":
      pending.push(load.companies(mode, preset));
      break;
    case "bridges":
      pending.push(load.bridges(mode));
      break;
    case "funding":
      pending.push(load.funding(mode));
      break;
    case "precision":
      pending.push(load.precision());
      break;
  }
  pending.forEach((p) => p.catch(() => undefined));
}

// Standalone pages never wait for /api/meta, so they name the product themselves.
const PRODUCT = "BlueWatch";

export function RouteView({ route }: { route: Route }) {
  const page = pageOf(route);
  if (route.name === "not_found" || isStandalone(route) || page === null) return <NotFound />;
  return (
    <Suspense fallback={<ScreenSkeleton route={page} detail={opensRecord(route)} />}>
      <Screen route={route} />
    </Suspense>
  );
}

type ScreenRoute = Exclude<Route, { name: "not_found" } | StandaloneRoute>;

/** Pages of their own, outside the app shell: the student form an invitation link opens, and the guide. */
export function StandalonePage({ route }: { route: StandaloneRoute }) {
  const { t } = useT(shellMessages);
  usePageTitle(t(route.name === "apply" ? "page_apply" : "page_guide"), PRODUCT);
  return (
    <Suspense fallback={<BootScreen />}>
      {route.name === "apply" ? (
        <ApplyScreen preset={route.preset ?? "blue"} />
      ) : (
        <GuideScreen track={route.track} />
      )}
    </Suspense>
  );
}

/** A company or a bridge is open, so the loading shape includes its detail panel. */
function opensRecord(route: ScreenRoute): boolean {
  switch (route.name) {
    case "surfacing":
    case "companies":
      return route.companyId !== undefined;
    case "card":
      return true;
    case "bridges":
      return route.bridgeId !== undefined;
    case "ideas":
      return route.itemId !== undefined;
    default:
      return false;
  }
}

function Screen({ route }: { route: ScreenRoute }) {
  switch (route.name) {
    case "surfacing":
      return <SurfacingScreen companyId={route.companyId} tab={route.tab} />;
    case "companies":
      return <CompaniesScreen companyId={route.companyId} tab={route.tab} />;
    case "card":
      return (
        <div className="page">
          <VentureCardView
            companyId={route.companyId}
            tab={route.tab ?? "overview"}
            layout="page"
            onTabChange={(tab) => navigate({ name: "card", companyId: route.companyId, tab })}
          />
        </div>
      );
    case "bridges":
      return <BridgesScreen bridgeId={route.bridgeId} />;
    case "funding":
      return <FundingScreen />;
    case "founder":
      return <FounderScreen />;
    case "scout":
      return <ScoutScreen />;
    case "outreach":
      return <OutreachScreen />;
    case "precision":
      return <PrecisionScreen />;
    case "ideas":
      return <IdeasScreen itemId={route.itemId} />;
  }
}

function NotFound() {
  const meta = useMeta();
  const { t } = useT(shellMessages);
  return (
    <div className="page">
      <EmptyState
        icon={<Compass size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("notFoundTitle")}
        action={
          <a className="btn btn--primary" href="#/surfacing">
            {t("notFoundAction", { list: meta.listName })}
          </a>
        }
      >
        {t("notFoundBody")}
      </EmptyState>
    </div>
  );
}
