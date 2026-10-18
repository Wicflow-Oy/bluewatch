// Hash routes, so the built app works from any static host and deep links survive a reload.
import { useSyncExternalStore } from "react";
import type { PresetName } from "./preset";

export const CARD_TABS = ["overview", "evidence", "opportunities", "outreach"] as const;
export type CardTab = (typeof CARD_TABS)[number];

export type Route =
  | { name: "surfacing"; companyId?: string; tab?: CardTab }
  | { name: "companies"; companyId?: string; tab?: CardTab }
  | { name: "card"; companyId: string; tab?: CardTab }
  | { name: "bridges"; bridgeId?: string }
  | { name: "funding" }
  | { name: "founder" }
  | { name: "scout" }
  | { name: "outreach" }
  | { name: "precision" }
  | { name: "ideas"; itemId?: string }
  | { name: "apply"; preset?: PresetName }
  | { name: "guide"; track?: string }
  | { name: "not_found" };

export type RouteName = Route["name"];
/** The routes that are pages of their own in the navigation. The student form and the guide stand
 * outside the app. */
export type PageName = Exclude<RouteName, "card" | "apply" | "guide" | "not_found">;
export type StandaloneRoute = Extract<Route, { name: "apply" | "guide" }>;

const SIMPLE = ["funding", "founder", "scout", "outreach", "precision"] as const;

function asTab(value: string | undefined): CardTab | undefined {
  return CARD_TABS.find((t) => t === value);
}

export function parseHash(hash: string): Route {
  const [path, query = ""] = hash.split("?");
  const [name = "", rawId, rawTab] = path
    .replace(/^#\/?/, "")
    .split("/")
    .filter(Boolean)
    .map((part) => {
      try {
        return decodeURIComponent(part);
      } catch {
        return part;
      }
    });
  if (name === "" || name === "surfacing")
    return { name: "surfacing", companyId: rawId, tab: asTab(rawTab) };
  if (name === "companies") return { name: "companies", companyId: rawId, tab: asTab(rawTab) };
  if (name === "card")
    return rawId ? { name: "card", companyId: rawId, tab: asTab(rawTab) } : { name: "companies" };
  if (name === "bridges") return { name: "bridges", bridgeId: rawId };
  if (name === "ideas") return { name: "ideas", itemId: rawId };
  if (name === "guide") return { name: "guide", track: rawId };
  if (name === "apply") {
    const preset = new URLSearchParams(query).get("preset");
    return preset === "climate_circular" ? { name: "apply", preset } : { name: "apply" };
  }
  const simple = SIMPLE.find((s) => s === name);
  return simple ? { name: simple } : { name: "not_found" };
}

export function href(route: Route): string {
  const enc = encodeURIComponent;
  switch (route.name) {
    case "surfacing":
    case "companies": {
      const id = route.companyId ? `/${enc(route.companyId)}` : "";
      const tab = route.companyId && route.tab && route.tab !== "overview" ? `/${route.tab}` : "";
      return `#/${route.name}${id}${tab}`;
    }
    case "card": {
      const tab = route.tab && route.tab !== "overview" ? `/${route.tab}` : "";
      return `#/card/${enc(route.companyId)}${tab}`;
    }
    case "bridges":
      return `#/bridges${route.bridgeId ? `/${enc(route.bridgeId)}` : ""}`;
    case "ideas":
      return `#/ideas${route.itemId ? `/${enc(route.itemId)}` : ""}`;
    case "apply":
      return `#/apply${route.preset && route.preset !== "blue" ? `?preset=${route.preset}` : ""}`;
    case "guide":
      return `#/guide${route.track ? `/${enc(route.track)}` : ""}`;
    case "not_found":
      return "#/surfacing";
    default:
      return `#/${route.name}`;
  }
}

export function navigate(route: Route): void {
  const next = href(route);
  if (window.location.hash !== next) window.location.hash = next;
}

/** Like navigate(), but React has rendered the new route when it returns (for view transitions). */
export function navigateNow(route: Route): void {
  const next = href(route);
  if (window.location.hash === next) return;
  window.history.pushState(null, "", next);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

function subscribe(notify: () => void) {
  window.addEventListener("hashchange", notify);
  return () => window.removeEventListener("hashchange", notify);
}

export function useHash(): string {
  return useSyncExternalStore(subscribe, () => window.location.hash);
}

export function useRoute(): Route {
  return parseHash(useHash());
}

/** The nav page a route belongs to: a full-page card sits under Companies. */
export function pageOf(route: Route): PageName | null {
  if (route.name === "card") return "companies";
  return route.name === "not_found" || isStandalone(route) ? null : route.name;
}

/** The student form and the guide: pages of their own, without the app shell. */
export function isStandalone(route: Route): route is StandaloneRoute {
  return route.name === "apply" || route.name === "guide";
}

/** The top-level page for a nav item. */
export function pageHref(name: PageName): string {
  return `#/${name}`;
}

export function openPage(name: PageName): void {
  window.location.hash = pageHref(name);
}
