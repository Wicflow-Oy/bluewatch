import {
  Anchor,
  Building2,
  IdCard,
  Landmark,
  Send,
  Target,
  Telescope,
  Waves,
  Waypoints,
  type LucideIcon,
} from "lucide-react";
import { translator } from "../i18n/messages";
import type { PageName } from "../lib/router";
import { shellMessages } from "./messages";

export const SECTIONS = ["discover", "engage", "quality"] as const;

export interface NavItem {
  route: PageName;
  icon: LucideIcon;
  section: (typeof SECTIONS)[number];
  /** In the top bar's pills; the rest sit under "More". */
  primary?: boolean;
  /** In the phone tab bar; the rest sit in the More sheet. */
  tab?: boolean;
}

// The radar's loop is primary: what surfaced, the whole set, why to act now, which money fits, and the
// pipeline that feeds it. Tools and quality checks sit under "More".
export const NAV: NavItem[] = [
  { route: "surfacing", icon: Waves, section: "discover", primary: true, tab: true },
  { route: "companies", icon: Building2, section: "discover", primary: true, tab: true },
  { route: "bridges", icon: Waypoints, section: "discover", primary: true, tab: true },
  { route: "funding", icon: Landmark, section: "discover", primary: true, tab: true },
  { route: "ideas", icon: Anchor, section: "engage", primary: true },
  { route: "founder", icon: IdCard, section: "engage" },
  { route: "outreach", icon: Send, section: "engage" },
  { route: "scout", icon: Telescope, section: "engage" },
  { route: "precision", icon: Target, section: "quality" },
];

/** A page's name in the interface language; the list's own name comes from /api/meta. */
export function pageLabel(route: PageName, listName: string): string {
  return route === "surfacing" ? listName : translator(shellMessages).t(`page_${route}`);
}

export function navLabel(item: NavItem, listName: string): string {
  return pageLabel(item.route, listName);
}

/** The short label in pills and tabs: Surfacing is "Surfacing", not the list's long name. */
export function pillLabel(route: PageName, listName: string): string {
  return route === "surfacing"
    ? translator(shellMessages).t("tab_surfacing")
    : pageLabel(route, listName);
}
