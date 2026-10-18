// The top bar's navigation: an ink segmented row of page links with a sliding indicator, and a "More" pill
// that holds the tools and quality checks. When a More page is open, the pill carries its name.
import { Check, ChevronDown } from "lucide-react";
import { Suspense, use, useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ideasQueue, load } from "../data";
import { useLang } from "../i18n/lang";
import { useT } from "../i18n/messages";
import { useMeta } from "../lib/meta";
import { pageHref, type PageName } from "../lib/router";
import { Boundary } from "../ui/Boundary";
import { useSlidingIndicator } from "../ui/useSlidingIndicator";
import { shellMessages } from "./messages";
import { NAV, pillLabel } from "./nav";
import { useDismiss } from "./useDismiss";
import { useSettledScope } from "./useSettledScope";
import "../ui/Segmented.css";
import "./Popover.css";
import "./NavPills.css";

const PRIMARY = NAV.filter((n) => n.primary);
const MORE = NAV.filter((n) => !n.primary);

function NavCount({ route }: { route: PageName }) {
  const { mode, preset } = useSettledScope();
  const list = use(load.list(mode, preset)).data;
  const bridges = use(load.bridges(mode)).data;
  const count =
    route === "surfacing" ? list.entries.length : route === "bridges" ? bridges.length : null;
  return count === null ? null : <span className="seg__ct nav-pills__count">{count}</span>;
}

/** Idea Harbour's Top N for this workspace and preset. It is read again when the tab regains focus,
 * so an idea shared from the student form in another tab shows in the count; nothing shows while the
 * queue can't be read. */
function IdeasCount() {
  const { mode, preset } = useSettledScope();
  const key = `${mode}:${preset}`;
  const [count, setCount] = useState<{ key: string; top: number | null } | null>(null);
  const [visits, setVisits] = useState(0);
  useEffect(() => {
    const onFocus = () => setVisits((n) => n + 1);
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);
  useEffect(() => {
    let live = true;
    ideasQueue(mode, preset).then(
      (queue) => live && setCount({ key, top: queue.top_ids.length }),
      () => live && setCount({ key, top: null }),
    );
    return () => {
      live = false;
    };
  }, [key, mode, preset, visits]);
  if (count?.key !== key || count.top === null) return null;
  return <span className="seg__ct nav-pills__count">{count.top}</span>;
}

function Count({ route }: { route: PageName }) {
  if (route === "ideas") return <IdeasCount />;
  if (route !== "surfacing" && route !== "bridges") return null;
  return (
    <Boundary fallback={null}>
      <Suspense fallback={null}>
        <NavCount route={route} />
      </Suspense>
    </Boundary>
  );
}

function MoreMenu({ current, listName }: { current: PageName | null; listName: string }) {
  const { t } = useT(shellMessages);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<(HTMLAnchorElement | null)[]>([]);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(rootRef, open, close, triggerRef);
  const active = MORE.find((n) => n.route === current);

  const onMenuKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const at = itemRefs.current.findIndex((el) => el === document.activeElement);
    const next = (at + (e.key === "ArrowDown" ? 1 : -1) + MORE.length) % MORE.length;
    itemRefs.current[next]?.focus();
  };

  return (
    <div className="nav-more" ref={rootRef} data-selected={Boolean(active)}>
      <button
        ref={triggerRef}
        type="button"
        className="seg__btn nav-more__trigger"
        data-selected={Boolean(active)}
        aria-current={active ? "page" : undefined}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span>{active ? pillLabel(active.route, listName) : t("more")}</span>
        <ChevronDown size={12} strokeWidth={1.75} aria-hidden="true" />
      </button>
      {open && (
        <div
          className="popover popover--end nav-more__menu"
          role="menu"
          aria-label={t("more")}
          onKeyDown={onMenuKey}
        >
          {MORE.map((item, i) => {
            const Icon = item.icon;
            const on = item.route === current;
            return (
              <a
                key={item.route}
                ref={(el) => {
                  itemRefs.current[i] = el;
                }}
                role="menuitem"
                className="menu-row"
                href={pageHref(item.route)}
                aria-current={on ? "page" : undefined}
                autoFocus={on || (!active && i === 0)}
                onClick={close}
              >
                <Icon size={16} strokeWidth={1.5} aria-hidden="true" />
                <span className="menu-row__label">{pillLabel(item.route, listName)}</span>
                {on && <Check size={16} strokeWidth={1.75} aria-hidden="true" />}
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function NavPills({ current }: { current: PageName | null }) {
  const meta = useMeta();
  const lang = useLang();
  const { t } = useT(shellMessages);
  const { rootRef, indRef } = useSlidingIndicator<HTMLElement>(current, `${lang}:${meta.listName}`);

  return (
    <nav className="seg seg--ink nav-pills" aria-label={t("mainNav")} ref={rootRef}>
      <span className="seg__ind" ref={indRef} aria-hidden="true" />
      {PRIMARY.map((item) => {
        const on = current === item.route;
        return (
          <a
            key={item.route}
            className="seg__btn"
            href={pageHref(item.route)}
            aria-current={on ? "page" : undefined}
            data-selected={on}
          >
            <span>{pillLabel(item.route, meta.listName)}</span>
            <Count route={item.route} />
          </a>
        );
      })}
      <MoreMenu current={current} listName={meta.listName} />
    </nav>
  );
}
