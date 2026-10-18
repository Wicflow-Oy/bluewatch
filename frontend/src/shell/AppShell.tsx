import { Component, Suspense, useCallback, useEffect, useRef, type ReactNode } from "react";
import { RefreshCw, TriangleAlert } from "lucide-react";
import { translator, useT } from "../i18n/messages";
import { useMeta } from "../lib/meta";
import { pageOf, useRoute } from "../lib/router";
import { RouteView } from "../screens/pages";
import { ErrorState, Skeleton } from "../ui/States";
import { BottomTabs } from "./BottomTabs";
import { CommandPalette, rememberCompany } from "./CommandPalette";
import { closeLayer, openLayer, useLayer } from "./layers";
import { shellMessages } from "./messages";
import { pageLabel } from "./nav";
import { TopBar } from "./TopBar";
import { usePageTitle } from "./usePageTitle";
import "./AppShell.css";

/** Catches a page that fails to render, so the shell (navigation, search) keeps working. */
class PageBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    // A class component cannot use hooks; the app re-renders it on a language switch all the same.
    const { t } = translator(shellMessages);
    return (
      <div className="page">
        <ErrorState
          icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
          title={t("pageFailedTitle")}
          action={
            <button type="button" className="btn" onClick={() => window.location.reload()}>
              <RefreshCw size={16} strokeWidth={1.5} aria-hidden="true" />
              {t("reload")}
            </button>
          }
        >
          {t("pageFailedBody")}
        </ErrorState>
      </div>
    );
  }
}

function PageSkeleton() {
  const { t } = useT(shellMessages);
  return (
    <div className="page" role="status" aria-label={t("loading")}>
      <Skeleton width={240} height={32} radius={8} style={{ marginTop: 16 }} />
      <Skeleton width={320} height={14} style={{ marginTop: 14 }} />
      <Skeleton height={320} radius={24} style={{ marginTop: 28 }} />
    </div>
  );
}

export function AppShell() {
  const route = useRoute();
  const meta = useMeta();
  const { t } = useT(shellMessages);
  const page = pageOf(route);
  usePageTitle(page ? pageLabel(page, meta.listName) : t("page_notFound"), meta.productName);
  const layer = useLayer();
  const scrollRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLElement>(null);
  const companyId = "companyId" in route ? route.companyId : undefined;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (layer === "palette") closeLayer("palette");
        else openLayer("palette");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [layer]);

  // A new page starts at the top; opening a drawer on the same page keeps the scroll position.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [route.name]);

  // The bar gets its hairline once content slides under it (written straight to the DOM, no re-render).
  useEffect(() => {
    const scroller = scrollRef.current;
    if (!scroller) return;
    const onScroll = () => {
      headerRef.current?.setAttribute("data-scrolled", String(scroller.scrollTop > 4));
    };
    onScroll();
    scroller.addEventListener("scroll", onScroll, { passive: true });
    return () => scroller.removeEventListener("scroll", onScroll);
  }, []);

  // Search offers the last companies opened, from this tab's memory.
  useEffect(() => {
    if (companyId) rememberCompany(companyId);
  }, [companyId]);

  const closePalette = useCallback(() => closeLayer("palette"), []);

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        {t("skipToContent")}
      </a>
      <div className="app__main" ref={scrollRef}>
        <TopBar current={page} onSearch={() => openLayer("palette")} headerRef={headerRef} />
        <main id="main" className="app__content" tabIndex={-1}>
          <PageBoundary key={route.name}>
            <Suspense fallback={<PageSkeleton />}>
              <RouteView route={route} />
            </Suspense>
          </PageBoundary>
        </main>
      </div>
      <BottomTabs current={page} />
      {layer === "palette" && <CommandPalette onClose={closePalette} />}
    </div>
  );
}
