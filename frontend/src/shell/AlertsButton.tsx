// The alerts bell: deadlines 30 and 14 days out, and register signals on listed companies. The API
// sends one alert per company, so alerts with the same trigger, action and deadline are grouped and
// the companies listed once. What a viewer has seen is kept in this browser only.
import { Bell, X } from "lucide-react";
import {
  Suspense,
  use,
  useCallback,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import type { Alert } from "../contracts";
import { dataOrNull, load } from "../data";
import { translator, useT } from "../i18n/messages";
import { companyIdLabel, humanText } from "../lib/format";
import { useIsPhone } from "../lib/media";
import { useMeta } from "../lib/meta";
import { href } from "../lib/router";
import { Chip } from "../ui/Chip";
import { Deadline } from "../ui/Deadline";
import { Drawer } from "../ui/Drawer";
import { EmptyState } from "../ui/States";
import { TabPanel, Tabs } from "../ui/Tabs";
import { closeLayer, openLayer, useLayer } from "./layers";
import { shellMessages } from "./messages";
import { useDismiss } from "./useDismiss";
import { useSettledScope } from "./useSettledScope";
import "./Popover.css";
import "./AlertsButton.css";

// ---- seen state: alert ids, in localStorage only (never sent anywhere)

const SEEN_KEY = "bluewatch.alerts.seen";

function readSeen(): ReadonlySet<string> {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(SEEN_KEY) ?? "[]");
    return new Set(Array.isArray(parsed) ? parsed.filter((v) => typeof v === "string") : []);
  } catch {
    return new Set(); // blocked or corrupt storage: everything counts as unseen
  }
}

let seen = readSeen();
const seenListeners = new Set<() => void>();

function markSeen(ids: string[]): void {
  if (ids.every((id) => seen.has(id))) return;
  seen = new Set([...seen, ...ids]);
  try {
    window.localStorage.setItem(SEEN_KEY, JSON.stringify([...seen]));
  } catch {
    // Remembering what was seen is a convenience only.
  }
  seenListeners.forEach((notify) => notify());
}

function useSeen(): ReadonlySet<string> {
  return useSyncExternalStore(
    (notify) => {
      seenListeners.add(notify);
      return () => seenListeners.delete(notify);
    },
    () => seen,
  );
}

// ---- grouping

type Tab = "deadlines" | "signals";

interface AlertGroup {
  key: string;
  tab: Tab;
  trigger: string;
  action: string;
  deadline: string | null;
  alertIds: string[];
  companyIds: string[];
  high: boolean;
}

function groupAlerts(alerts: Alert[]): AlertGroup[] {
  const groups = new Map<string, AlertGroup>();
  for (const a of alerts) {
    const deadline = a.deadline ?? null;
    const key = `${a.trigger}|${a.next_action}|${deadline ?? ""}`;
    const group = groups.get(key) ?? {
      key,
      tab: a.trigger.startsWith("deadline_") ? "deadlines" : "signals",
      trigger: a.trigger,
      action: a.next_action,
      deadline,
      alertIds: [],
      companyIds: [],
      high: false,
    };
    group.alertIds.push(a.id);
    if (!group.companyIds.includes(a.company_id)) group.companyIds.push(a.company_id);
    group.high ||= a.priority === "high";
    groups.set(key, group);
  }
  // Soonest deadline first; undated signals keep the API's order after them.
  return [...groups.values()].sort((a, b) =>
    (a.deadline ?? "9999").localeCompare(b.deadline ?? "9999"),
  );
}

const isUnseen = (group: AlertGroup, seenIds: ReadonlySet<string>) =>
  group.alertIds.some((id) => !seenIds.has(id));

const SIGNAL_TYPES = [
  "newly_founded",
  "share_issue",
  "award",
  "open_tender",
  "eu_project",
  "eu_grant_signed",
  "new_hostname",
  "call_open",
  "project_published",
  "site_change",
] as const;

/** "new_newly_founded" -> "Newly founded": the register event behind a signal alert. */
function signalLabel(trigger: string): string {
  const type = SIGNAL_TYPES.find((s) => s === trigger.replace(/^new_/, ""));
  if (type) return translator(shellMessages).t(`signal_${type}`);
  const words = humanText(trigger.replace(/^new_/, ""));
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// ---- rows

interface CompanyLink {
  name: string;
  href: string;
}

type LinkFor = (companyId: string) => CompanyLink;

function useCompanyLinks(): LinkFor {
  const { mode, preset } = useSettledScope();
  const list = use(load.list(mode, preset)).data;
  const companies = use(dataOrNull(load.companies(mode, preset))) ?? [];
  return (companyId) => {
    const listed = list.entries.find((e) => e.company_id === companyId);
    const row = companies.find((c) => c.id === companyId);
    return {
      name: listed?.name ?? row?.name ?? companyIdLabel(companyId),
      href: href(listed ? { name: "surfacing", companyId } : { name: "card", companyId }),
    };
  };
}

const SHOWN_NAMES = 3;

// The row's colour bar: amber two weeks out, blue a month out, violet for register signals.
const BAR_TONES: Record<string, string> = { deadline_14d: "soon", deadline_30d: "month" };

interface GroupRowProps {
  group: AlertGroup;
  linkFor: LinkFor;
  unseen: boolean;
  onOpen: () => void;
}

function GroupRow({ group, linkFor, unseen, onOpen }: GroupRowProps) {
  const meta = useMeta();
  const { t, tn } = useT(shellMessages);
  const links = group.companyIds.map(linkFor);
  const more = links.length - SHOWN_NAMES;
  const tone = BAR_TONES[group.trigger] ?? "signal";
  const count = tn("listedCompanies", links.length);

  return (
    <li className={`alert-group alert-group--${tone}`}>
      <div className="alert-group__body">
        <p className="alert-group__action">{humanText(group.action)}</p>
        <p className="alert-group__meta">
          {group.deadline ? (
            <Deadline date={group.deadline} today={meta.today} />
          ) : (
            <Chip tone="violet">{signalLabel(group.trigger)}</Chip>
          )}
          <span>· {count}</span>
        </p>
        <p className="alert-group__names">
          {links.slice(0, SHOWN_NAMES).map((link, i) => (
            <span key={link.href}>
              {i > 0 && ", "}
              <a href={link.href} onClick={onOpen}>
                {link.name}
              </a>
            </span>
          ))}
          {more > 0 && <span className="alert-group__more"> +{more}</span>}
        </p>
      </div>
      {unseen && (
        <span className="alert-group__dot">
          <span className="sr-only">{t("notSeen")}</span>
        </span>
      )}
    </li>
  );
}

// ---- the panel (popover on desktop, sheet on phones)

function NoAlerts() {
  const { t } = useT(shellMessages);
  return (
    <EmptyState compact title={t("noAlertsTitle")}>
      {t("noAlertsBody")}
    </EmptyState>
  );
}

interface AlertsPanelProps {
  groups: AlertGroup[];
  linkFor: LinkFor;
  tab: Tab;
  onTab: (tab: Tab) => void;
  onClose: () => void;
  closeButton?: ReactNode;
}

function AlertsPanel({ groups, linkFor, tab, onTab, onClose, closeButton }: AlertsPanelProps) {
  const { t } = useT(shellMessages);
  const seenIds = useSeen();
  const deadlines = groups.filter((g) => g.tab === "deadlines");
  const signals = groups.filter((g) => g.tab === "signals");
  const shown = tab === "deadlines" ? deadlines : signals;
  const allIds = groups.flatMap((g) => g.alertIds);
  const anyUnseen = groups.some((g) => isUnseen(g, seenIds));

  return (
    <>
      <div className="popover__head alerts__head">
        <h2 className="popover__title">{t("alerts")}</h2>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          disabled={!anyUnseen}
          onClick={() => markSeen(allIds)}
        >
          {t("markAllSeen")}
        </button>
        {closeButton}
      </div>
      {groups.length === 0 ? (
        <NoAlerts />
      ) : (
        <>
          <div className="alerts__tabs">
            <Tabs
              label={t("alertKinds")}
              idPrefix="alerts"
              value={tab}
              onChange={onTab}
              tabs={[
                { id: "deadlines", label: t("deadlines"), count: deadlines.length },
                { id: "signals", label: t("newSignals"), count: signals.length },
              ]}
            />
          </div>
          <div className="alerts__scroll">
            <TabPanel idPrefix="alerts" tab={tab}>
              {shown.length === 0 ? (
                <NoAlerts />
              ) : (
                <ul className="alerts__list">
                  {shown.map((g) => (
                    <GroupRow
                      key={g.key}
                      group={g}
                      linkFor={linkFor}
                      unseen={isUnseen(g, seenIds)}
                      onOpen={() => {
                        markSeen(g.alertIds);
                        onClose();
                      }}
                    />
                  ))}
                </ul>
              )}
            </TabPanel>
          </div>
        </>
      )}
      <p className="popover__foot">{t("alertsNote")}</p>
    </>
  );
}

// ---- the bell

function AlertsBell() {
  const { t, tn } = useT(shellMessages);
  const { mode } = useSettledScope();
  const alerts = use(dataOrNull(load.alerts(mode)));
  const linkFor = useCompanyLinks();
  const seenIds = useSeen();
  const open = useLayer() === "alerts";
  const isPhone = useIsPhone();
  const [tab, setTab] = useState<Tab>("deadlines");
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => closeLayer("alerts"), []);
  useDismiss(rootRef, open && !isPhone, close, triggerRef);
  const groups = useMemo(() => groupAlerts(alerts ?? []), [alerts]);

  // No route and no recording: no bell at all, never a dead control.
  if (alerts === null) return null;

  const badge = groups.filter((g) => g.high && isUnseen(g, seenIds)).length;
  const panel = (closeButton?: ReactNode) => (
    <AlertsPanel
      groups={groups}
      linkFor={linkFor}
      tab={tab}
      onTab={setTab}
      onClose={close}
      closeButton={closeButton}
    />
  );

  return (
    <div className="alerts" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="icon-btn alerts__bell"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => (open ? close() : openLayer("alerts"))}
      >
        <Bell size={16} strokeWidth={1.5} aria-hidden="true" />
        {badge > 0 && (
          <span className="alerts__badge mono" aria-hidden="true">
            {badge}
          </span>
        )}
        <span className="sr-only">{badge > 0 ? tn("alertsUnseen", badge) : t("alerts")}</span>
      </button>
      {isPhone ? (
        <Drawer open={open} onClose={close} label={t("alerts")} variant="sheet">
          <div className="alerts__sheet">
            {panel(
              <button type="button" className="icon-btn alerts__close" onClick={close}>
                <X size={18} strokeWidth={1.5} aria-hidden="true" />
                <span className="sr-only">{t("closeAlerts")}</span>
              </button>,
            )}
          </div>
        </Drawer>
      ) : (
        open && (
          <div
            className="popover popover--end alerts__popover"
            role="dialog"
            aria-label={t("alerts")}
          >
            {panel()}
          </div>
        )
      )}
    </div>
  );
}

/** The bell with its popover (a sheet on phones). Hidden when alerts can't be loaded. */
export function AlertsButton() {
  return (
    <Suspense fallback={null}>
      <AlertsBell />
    </Suspense>
  );
}
