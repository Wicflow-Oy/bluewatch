// ⌘K / Ctrl+K: jump to a company (by name or business ID), a bridge, a funding instrument or a page,
// look up any Finnish, Norwegian or Estonian business ID, or run a shell action. What the visitor
// types stays in this component's memory; a lookup hands the ID to Founder view in memory too.
import {
  ArrowRight,
  Bell,
  Building2,
  CornerDownLeft,
  FilePen,
  History,
  Landmark,
  Languages,
  Layers,
  List,
  Moon,
  Repeat,
  Search,
  Sun,
  Waypoints,
} from "lucide-react";
import {
  Suspense,
  use,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";
import type { Country, Mode } from "../api";
import type { FundingCatalogue } from "../contracts";
import { dataOrNull, load } from "../data";
import { LANGS, useLang } from "../i18n/lang";
import { translator, useT } from "../i18n/messages";
import { formatBusinessId, registryLabel, registryName } from "../lib/format";
import { setFounderPrefill, setFundingFocus } from "../lib/handoff";
import { bridgeType, countryName, WORKSPACES, type Group } from "../lib/labels";
import { useMeta } from "../lib/meta";
import { setTheme, useTheme } from "../lib/theme";
import { presetShort, usePreset, type PresetName } from "../lib/preset";
import { navigate, openPage, type PageName } from "../lib/router";
import { useWorkspace } from "../lib/workspace";
import { CountryCode, GroupChip } from "../ui/Chip";
import { Kbd, Skeleton } from "../ui/States";
import { switchLanguage } from "./LanguageSwitch";
import { openLayer } from "./layers";
import { shellMessages } from "./messages";
import { NAV, navLabel, pageLabel } from "./nav";
import { useSwitchWorkspace } from "./WorkspaceSwitcher";
import "./CommandPalette.css";

type Section = "lookup" | "recent" | "companies" | "bridges" | "funding" | "goto" | "actions";

/** Companies, bridges and funding are headed by their page's name. */
function sectionHeading(section: Section, listName: string): string {
  if (section === "companies" || section === "bridges" || section === "funding")
    return pageLabel(section, listName);
  return translator(shellMessages).t(`section_${section}`);
}

interface Item {
  id: string;
  section: Section;
  icon: ReactNode;
  title: string;
  subtitle?: ReactNode;
  trailing?: ReactNode;
  haystack: string;
  run: () => void;
}

const ICON = { size: 16, strokeWidth: 1.5, "aria-hidden": true } as const;
const PER_SECTION = 6;

function normalise(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

const compactId = (id: string) => id.replace(/[\s-]/g, "");

function matches(item: Item, query: string): boolean {
  return normalise(query)
    .split(/\s+/)
    .filter(Boolean)
    .every((t) => item.haystack.includes(t));
}

// ---- recently opened companies: this tab's memory only

const RECENT_MAX = 3;
let recent: string[] = [];

/** Called by the shell whenever a company opens (drawer or full page). */
export function rememberCompany(companyId: string): void {
  recent = [companyId, ...recent.filter((id) => id !== companyId)].slice(0, RECENT_MAX);
}

// ---- business-ID lookups (spec §4.4)

const ID_FORMATS: { country: Country; pattern: RegExp }[] = [
  { country: "FI", pattern: /^\d{7}-?\d$/ },
  { country: "NO", pattern: /^\d{3}\s?\d{3}\s?\d{3}$/ },
  { country: "EE", pattern: /^\d{8}$/ },
];

function lookupItems(query: string): Item[] {
  const { t } = translator(shellMessages);
  const q = query.trim();
  return ID_FORMATS.filter((f) => f.pattern.test(q)).map(({ country }) => {
    const digits = compactId(q);
    const businessId = country === "FI" ? `${digits.slice(0, 7)}-${digits.slice(7)}` : digits;
    const shown = formatBusinessId(country, businessId);
    return {
      id: `l-${country}`,
      section: "lookup",
      icon: <Search {...ICON} />,
      title: t("lookUpTitle", { id: shown, registry: registryName(country) }),
      subtitle: t("lookUpSubtitle", { country: countryName(country) }),
      haystack: "",
      run: () => {
        setFounderPrefill({ country, businessId });
        openPage("founder");
      },
    };
  });
}

// ---- everything searchable

interface CompanyHit {
  id: string;
  name: string;
  country: string;
  registryId: string;
  group: Group;
  listed: boolean;
}

function companyItem(c: CompanyHit, section: Section): Item {
  return {
    id: `${section}-${c.id}`,
    section,
    icon: <Building2 {...ICON} />,
    title: c.name,
    subtitle: (
      <>
        <CountryCode code={c.country} />
        <span className="mono">{registryLabel(c.country, c.registryId)}</span>
      </>
    ),
    trailing: <GroupChip group={c.group} />,
    haystack: normalise(
      `${c.name} ${c.country} ${c.registryId} ${compactId(c.registryId)} ${formatBusinessId(c.country, c.registryId)}`,
    ),
    run: () =>
      navigate(
        c.listed ? { name: "surfacing", companyId: c.id } : { name: "card", companyId: c.id },
      ),
  };
}

function showAll(section: Section, page: PageName, label: string): Item {
  return {
    id: `all-${section}`,
    section,
    icon: <List {...ICON} />,
    title: translator(shellMessages).t("showAll", { label }),
    haystack: "",
    run: () => openPage(page),
  };
}

/** The funding catalogue is large (every instrument with its tiers), so search opens without it and
 * adds the Funding section once it has arrived. */
function useFundingWhenReady(mode: Mode): FundingCatalogue | null {
  const [loaded, setLoaded] = useState<{ mode: Mode; data: FundingCatalogue | null } | null>(null);
  useEffect(() => {
    let current = true;
    dataOrNull(load.funding(mode)).then((data) => current && setLoaded({ mode, data }));
    return () => {
      current = false;
    };
  }, [mode]);
  return loaded?.mode === mode ? loaded.data : null;
}

interface Catalogue {
  companies: CompanyHit[];
  bridges: Item[];
  funding: Item[];
  pages: Item[];
  actions: Item[];
}

function useCatalogue(): Catalogue {
  const { mode } = useWorkspace();
  const meta = useMeta();
  const { t } = useT(shellMessages);
  const switchTo = useSwitchWorkspace();
  const { preset, setPreset } = usePreset();
  const lang = useLang();
  const theme = useTheme();
  // Start every load before reading any, so they run in parallel.
  const listing = load.list(mode, preset);
  const companiesLoad = dataOrNull(load.companies(mode, preset));
  const bridgesLoad = dataOrNull(load.bridges(mode));
  const alertsLoad = dataOrNull(load.alerts(mode));
  const list = use(listing).data;
  const rows = use(companiesLoad);
  const bridges = use(bridgesLoad);
  const funding = useFundingWhenReady(mode);
  const alerts = use(alertsLoad);

  return useMemo(() => {
    const rowById = new Map((rows ?? []).map((r) => [r.id, r]));
    const listed: CompanyHit[] = list.entries.map((e) => ({
      id: e.company_id,
      name: e.name,
      country: e.country,
      registryId: rowById.get(e.company_id)?.registry_id ?? "",
      group: e.group,
      listed: true,
    }));
    const listedIds = new Set(listed.map((c) => c.id));
    const others: CompanyHit[] = [...rowById.values()]
      .filter((r) => !listedIds.has(r.id))
      .map((r) => ({
        id: r.id,
        name: r.name,
        country: r.country,
        registryId: r.registry_id,
        group: r.group,
        listed: false,
      }));

    const bridgeItems: Item[] = (bridges ?? []).map((b) => {
      const seed = /^B\d+$/.test(b.id);
      const parties = `${b.company.name} → ${b.counterparty.name}`;
      return {
        id: `b-${b.id}`,
        section: "bridges",
        icon: <Waypoints {...ICON} />,
        // Generated bridges have long internal ids; only the seed bridges' short ids are shown.
        title: seed ? `${b.id} · ${parties}` : parties,
        subtitle: bridgeType(b.type).label,
        haystack: normalise(`${seed ? b.id : ""} ${parties} ${bridgeType(b.type).label}`),
        run: () => navigate({ name: "bridges", bridgeId: b.id }),
      };
    });

    const fundingItems: Item[] = (funding?.instruments ?? []).map((f) => ({
      id: `f-${f.id}`,
      section: "funding",
      icon: <Landmark {...ICON} />,
      title: f.name,
      subtitle: f.funder ?? undefined,
      haystack: normalise(`${f.name} ${f.funder ?? ""}`),
      run: () => {
        setFundingFocus(f.id);
        openPage("funding");
      },
    }));

    const pages: Item[] = NAV.map((n) => {
      const Icon = n.icon;
      const label = navLabel(n, meta.listName);
      return {
        id: `p-${n.route}`,
        section: "goto",
        icon: <Icon {...ICON} />,
        title: label,
        haystack: normalise(`${t("goTo")} ${label} ${n.route}`),
        run: () => openPage(n.route),
      };
    });
    // The student form stands outside the app (it is what an invitation opens), so it isn't in NAV.
    pages.push({
      id: "p-apply",
      section: "goto",
      icon: <FilePen {...ICON} />,
      title: t("page_apply"),
      subtitle: t("studentFormSubtitle"),
      haystack: normalise(`${t("goTo")} ${t("page_apply")} apply idea harbour`),
      run: () => navigate({ name: "apply" }),
    });

    const otherMode: Mode = mode === "apelago" ? "redstone" : "apelago";
    const otherPreset: PresetName = preset === "blue" ? "climate_circular" : "blue";
    const actions: Item[] = [
      {
        id: "a-workspace",
        section: "actions",
        icon: <Repeat {...ICON} />,
        title: t("switchTo", { name: WORKSPACES[otherMode].name }),
        haystack: normalise(`${t("switchTo", { name: WORKSPACES[otherMode].name })} workspace`),
        run: () => switchTo(otherMode),
      },
      {
        id: "a-preset",
        section: "actions",
        icon: <Layers {...ICON} />,
        title: t("switchPreset", { preset: presetShort(otherPreset) }),
        haystack: normalise(t("switchPreset", { preset: presetShort(otherPreset) })),
        run: () => setPreset(otherPreset),
      },
    ];
    // The other languages by their own names, so they are found in any language (and with a card open).
    for (const option of LANGS.filter((l) => l.code !== lang)) {
      const title = t("switchLanguage", { name: option.label });
      actions.push({
        id: `a-lang-${option.code}`,
        section: "actions",
        icon: <Languages {...ICON} />,
        title,
        haystack: normalise(`${title} ${option.code} language kieli språk`),
        run: () => switchLanguage(option.code),
      });
    }
    const nextTheme = theme === "graphite" ? "light" : "graphite";
    const themeTitle = t(nextTheme === "graphite" ? "switchToGraphite" : "switchToLight");
    actions.push({
      id: "a-theme",
      section: "actions",
      icon: nextTheme === "graphite" ? <Moon {...ICON} /> : <Sun {...ICON} />,
      title: themeTitle,
      haystack: normalise(`${themeTitle} ${t("theme")} theme dark light graphite`),
      run: () => setTheme(nextTheme),
    });
    if (alerts !== null) {
      actions.push({
        id: "a-alerts",
        section: "actions",
        icon: <Bell {...ICON} />,
        title: t("openAlerts"),
        haystack: normalise(`${t("openAlerts")} ${t("deadlines")} ${t("newSignals")}`),
        run: () => openLayer("alerts"),
      });
    }

    return {
      companies: [...listed, ...others],
      bridges: bridgeItems,
      funding: fundingItems,
      pages,
      actions,
    };
  }, [
    list,
    rows,
    bridges,
    funding,
    alerts,
    mode,
    preset,
    lang,
    theme,
    meta.listName,
    switchTo,
    setPreset,
    t,
  ]);
}

type ListedPage = "companies" | "bridges" | "funding";

/** At most six per section, with a "show all" row when a section has more. */
function capped(items: Item[], page: ListedPage, listName: string): Item[] {
  return items.length > PER_SECTION
    ? [...items.slice(0, PER_SECTION), showAll(page, page, pageLabel(page, listName))]
    : items;
}

function useResults(query: string): Item[] {
  const all = useCatalogue();
  const { listName } = useMeta();
  return useMemo(() => {
    if (!query.trim()) {
      const recentItems = recent
        .map((id) => all.companies.find((c) => c.id === id))
        .filter((c): c is CompanyHit => c !== undefined)
        .map((c) => ({ ...companyItem(c, "recent"), icon: <History {...ICON} /> }));
      return [...recentItems, ...all.actions];
    }
    const companyItems = all.companies.map((c) => companyItem(c, "companies"));
    const hit = (items: Item[]) => items.filter((i) => matches(i, query));
    return [
      ...lookupItems(query),
      ...capped(hit(companyItems), "companies", listName),
      ...capped(hit(all.bridges), "bridges", listName),
      ...capped(hit(all.funding), "funding", listName),
      ...hit(all.pages),
      ...hit(all.actions),
    ];
  }, [all, query, listName]);
}

interface ResultsProps {
  query: string;
  onClose: () => void;
  listId: string;
  input: RefObject<HTMLInputElement | null>;
}

function Results({ query, onClose, listId, input }: ResultsProps) {
  const { t } = useT(shellMessages);
  const { listName } = useMeta();
  const shown = useResults(query);
  const [active, setActive] = useState(0);
  const activeIndex = Math.min(active, Math.max(0, shown.length - 1));
  const listRef = useRef<HTMLUListElement>(null);

  // The input keeps focus; the keyboard drives the highlighted row through this handler.
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const delta = e.key === "ArrowDown" ? 1 : -1;
        setActive(
          (i) => (Math.min(i, shown.length - 1) + delta + shown.length) % Math.max(1, shown.length),
        );
      } else if (e.key === "Enter" && shown[activeIndex]) {
        e.preventDefault();
        onClose();
        shown[activeIndex].run();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [shown, activeIndex, onClose]);

  useEffect(() => {
    listRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
    // The input owns focus, so it announces the highlighted option.
    if (shown.length > 0)
      input.current?.setAttribute("aria-activedescendant", `${listId}-${activeIndex}`);
    else input.current?.removeAttribute("aria-activedescendant");
  }, [activeIndex, shown.length, listId, input]);

  if (shown.length === 0) {
    return <p className="palette__empty">{t("noMatch", { query })}</p>;
  }

  return (
    <ul
      className="palette__list"
      role="listbox"
      id={listId}
      ref={listRef}
      aria-label={t("results")}
    >
      {shown.map((item, i) => {
        const heading =
          i === 0 || shown[i - 1].section !== item.section
            ? sectionHeading(item.section, listName)
            : null;
        return (
          <li key={item.id} role="presentation">
            {heading && (
              <p className="palette__group overline" role="presentation">
                {heading}
              </p>
            )}
            <div
              role="option"
              id={`${listId}-${i}`}
              aria-selected={i === activeIndex}
              className="palette__item"
              onPointerMove={() => setActive(i)}
              onClick={() => {
                onClose();
                item.run();
              }}
            >
              <span className="palette__icon">{item.icon}</span>
              <span className="palette__text">
                <span className="palette__title">{item.title}</span>
                {item.subtitle && <span className="palette__subtitle">{item.subtitle}</span>}
              </span>
              {item.trailing}
              <ArrowRight size={14} strokeWidth={1.5} className="palette__go" aria-hidden="true" />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function CommandPalette({ onClose }: { onClose: () => void }) {
  const { t } = useT(shellMessages);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const returnTo = useRef<HTMLElement | null>(null);

  useEffect(() => {
    returnTo.current = document.activeElement as HTMLElement | null;
    inputRef.current?.focus();
    return () => returnTo.current?.focus?.({ preventScroll: true });
  }, []);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.stopPropagation();
      onClose();
    }
    if (e.key === "Tab") e.preventDefault(); // the palette is one field; keep focus in it
  };

  return createPortal(
    <div className="palette-root" onKeyDown={onKeyDown}>
      <div className="palette-scrim" onClick={onClose} aria-hidden="true" />
      <div className="palette" role="dialog" aria-modal="true" aria-label={t("search")}>
        <label className="palette__field">
          <Search size={16} strokeWidth={1.5} aria-hidden="true" />
          <input
            ref={inputRef}
            className="palette__input"
            placeholder={t("searchPlaceholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-autocomplete="list"
            aria-label={t("searchPlaceholder")}
          />
          <Kbd>esc</Kbd>
        </label>
        <Suspense
          fallback={
            <div className="palette__loading" role="status" aria-label={t("loadingSearch")}>
              <Skeleton height={40} radius={6} />
              <Skeleton height={40} radius={6} />
              <Skeleton height={40} radius={6} />
            </div>
          }
        >
          {/* A new query starts the highlight from the top again. */}
          <Results key={query} query={query} onClose={onClose} listId={listId} input={inputRef} />
        </Suspense>
        <footer className="palette__footer">
          <span>
            <Kbd>↑</Kbd>
            <Kbd>↓</Kbd> {t("keyMove")}
          </span>
          <span>
            <Kbd>
              <CornerDownLeft size={12} strokeWidth={2} aria-hidden="true" />
            </Kbd>{" "}
            {t("keyOpen")}
          </span>
        </footer>
      </div>
    </div>,
    document.body,
  );
}
