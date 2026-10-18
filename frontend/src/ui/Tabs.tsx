import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
} from "react";
import { useSlidingIndicator } from "./useSlidingIndicator";
import "./Segmented.css";
import "./Tabs.css";

export interface TabItem<T extends string> {
  id: T;
  label: string;
  count?: number;
}

interface TabsProps<T extends string> {
  tabs: TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  label: string;
  idPrefix: string;
  /** sm: 26px segments (popovers), md: 30px (default). */
  size?: "sm" | "md";
}

// Room left beside a tab scrolled into view, so the fade never covers its label.
const EDGE = 32;

/** Which ends of a scrolling tab row hide more tabs, for the edge fades. */
function hiddenEnds(list: HTMLElement): "start" | "end" | "both" | undefined {
  const start = list.scrollLeft > 1;
  const end = list.scrollLeft + list.clientWidth < list.scrollWidth - 1;
  return start && end ? "both" : start ? "start" : end ? "end" : undefined;
}

/** Keeps the selected tab and the edge fades right when the row is wider than its box (phones). */
function useTabRow(
  listRef: RefObject<HTMLDivElement | null>,
  tabRefs: RefObject<(HTMLButtonElement | null)[]>,
  selected: number,
) {
  const [more, setMore] = useState<ReturnType<typeof hiddenEnds>>();

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const update = () => setMore(hiddenEnds(list));
    const observer = new ResizeObserver(update);
    observer.observe(list);
    list.addEventListener("scroll", update, { passive: true });
    return () => {
      observer.disconnect();
      list.removeEventListener("scroll", update);
    };
  }, [listRef]);

  useEffect(() => {
    const list = listRef.current;
    const tabEl = tabRefs.current[selected];
    if (!list || !tabEl) return;
    const box = list.getBoundingClientRect();
    const tab = tabEl.getBoundingClientRect();
    if (tab.left < box.left) list.scrollLeft -= box.left - tab.left + EDGE;
    else if (tab.right > box.right) list.scrollLeft += tab.right - box.right + EDGE;
  }, [listRef, tabRefs, selected]);

  return more;
}

/** WAI-ARIA tabs: arrow keys move between tabs, the selected tab is the only tab stop. */
export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  label,
  idPrefix,
  size = "md",
}: TabsProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const itemsKey = tabs.map((t) => `${t.id}:${t.label}:${t.count ?? ""}`).join("|");
  const { rootRef: listRef, indRef } = useSlidingIndicator<HTMLDivElement>(value, itemsKey);
  const more = useTabRow(
    listRef,
    refs,
    tabs.findIndex((t) => t.id === value),
  );

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = tabs.findIndex((t) => t.id === value);
    const next =
      e.key === "ArrowRight"
        ? (i + 1) % tabs.length
        : e.key === "ArrowLeft"
          ? (i - 1 + tabs.length) % tabs.length
          : e.key === "Home"
            ? 0
            : e.key === "End"
              ? tabs.length - 1
              : -1;
    if (next < 0) return;
    e.preventDefault();
    onChange(tabs[next].id);
    refs.current[next]?.focus();
  };

  return (
    <div
      ref={listRef}
      className={`tabs seg${size === "sm" ? " seg--sm" : ""}`}
      role="tablist"
      aria-label={label}
      data-more={more}
      onKeyDown={onKeyDown}
    >
      <span className="seg__ind" ref={indRef} aria-hidden="true" />
      {tabs.map((tab, i) => {
        const selected = tab.id === value;
        return (
          <button
            key={tab.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`${idPrefix}-tab-${tab.id}`}
            aria-selected={selected}
            aria-controls={`${idPrefix}-panel`}
            tabIndex={selected ? 0 : -1}
            className="tabs__tab seg__btn"
            onClick={() => onChange(tab.id)}
          >
            {tab.label}
            {tab.count !== undefined && <span className="tabs__count seg__ct">{tab.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({
  idPrefix,
  tab,
  children,
}: {
  idPrefix: string;
  tab: string;
  children: ReactNode;
}) {
  return (
    <div
      role="tabpanel"
      id={`${idPrefix}-panel`}
      aria-labelledby={`${idPrefix}-tab-${tab}`}
      className="tab-panel"
      key={tab}
    >
      {children}
    </div>
  );
}
