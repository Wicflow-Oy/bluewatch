// A table people work in, laid out like a spreadsheet: a bordered sheet with a line around every cell, one
// line per row, row numbers, a header with an icon per column, one sort per column, rows that open on click
// or Enter, and J/K or the arrow keys to move between rows. The sheet scrolls inside its own box, so the
// header and the first two columns stay in view. Each row carries data-row-id for the card morph. Phones get
// stacked capsules instead, so the page never scrolls sideways.
import { ArrowDownWideNarrow, type LucideIcon } from "lucide-react";
import { useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { vars } from "../lib/motion";
import "./DataTable.css";

/** A fixed width in pixels, or a share of the room left over that never drops below `min` pixels. */
export type ColumnWidth = number | { min: number; fr?: number };

export interface Column<T> {
  id: string;
  header: string;
  icon?: LucideIcon;
  width: ColumnWidth;
  align?: "left" | "right";
  /** Stays in view when the sheet scrolls sideways (the name column). */
  pinned?: boolean;
  cell(r: T): ReactNode;
  /** The order this column sorts by, most useful first (newest, highest, soonest). */
  sort?(a: T, b: T): number;
}

interface DataTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  getRowId(r: T): string;
  selectedId?: string;
  onOpen(r: T): void;
  stackedRow(r: T): ReactNode;
  label: string;
}

/** The row-number column every sheet starts with. */
export const ROW_NUMBER_WIDTH = 48;

/** The CSS grid tracks for a set of widths, and the narrowest the sheet can be before it scrolls. */
export function sheetTracks(widths: ColumnWidth[]): { cols: string; minWidth: string } {
  const cols = widths
    .map((w) => (typeof w === "number" ? `${w}px` : `minmax(${w.min}px, ${w.fr ?? 1}fr)`))
    .join(" ");
  const min = widths.reduce<number>((sum, w) => sum + (typeof w === "number" ? w : w.min), 0);
  return { cols, minWidth: `${min}px` };
}

const NEXT_KEYS = new Set(["ArrowDown", "j", "J"]);
const PREVIOUS_KEYS = new Set(["ArrowUp", "k", "K"]);

export function DataTable<T>({
  rows,
  columns,
  getRowId,
  selectedId,
  onOpen,
  stackedRow,
  label,
}: DataTableProps<T>) {
  const [sortId, setSortId] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  const sorted = useMemo(() => {
    const order = columns.find((c) => c.id === sortId)?.sort;
    return order ? [...rows].sort(order) : rows;
  }, [rows, columns, sortId]);

  // One tab stop for the whole body: the focused row, else the open one, else the first.
  const ids = sorted.map(getRowId);
  const tabStop = [focusId, selectedId].find((id) => id && ids.includes(id)) ?? ids[0];

  const moveFocus = (index: number) => {
    const target = Math.max(0, Math.min(sorted.length - 1, index));
    const row = bodyRef.current?.querySelectorAll<HTMLElement>('[role="row"]')[target];
    row?.focus();
    row?.scrollIntoView({ block: "nearest" });
  };

  const onRowKeyDown = (e: KeyboardEvent<HTMLDivElement>, index: number) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (NEXT_KEYS.has(e.key)) moveFocus(index + 1);
    else if (PREVIOUS_KEYS.has(e.key)) moveFocus(index - 1);
    else if (e.key === "Home") moveFocus(0);
    else if (e.key === "End") moveFocus(sorted.length - 1);
    else if (e.key === "Enter" || e.key === " ") onOpen(sorted[index]);
    else return;
    e.preventDefault();
  };

  const { cols, minWidth } = sheetTracks([ROW_NUMBER_WIDTH, ...columns.map((c) => c.width)]);
  // The pinned columns stick at the row number's right edge, one after another.
  const pinLeft = new Map<string, number>();
  let left = ROW_NUMBER_WIDTH;
  for (const c of columns) {
    if (!c.pinned || typeof c.width !== "number") continue;
    pinLeft.set(c.id, left);
    left += c.width;
  }
  const cellClass = (c: Column<T>, base: string) =>
    `${base}${c.align === "right" ? " sheet__num" : ""}${pinLeft.has(c.id) ? " sheet__pin" : ""}`;
  const pinStyle = (c: Column<T>) =>
    pinLeft.has(c.id) ? vars({ "--pin-left": `${pinLeft.get(c.id)}px` }) : undefined;

  return (
    <div className="data-table">
      <div className="sheet sheet--tall" style={vars({ "--cols": cols, "--sheet-min": minWidth })}>
        <div className="sheet__grid" role="table" aria-label={label} aria-rowcount={sorted.length}>
          <div role="rowgroup" className="sheet__head">
            <div role="row" className="sheet__row sheet__row--head">
              <div role="columnheader" className="sheet__th sheet__rownum">
                <span className="sr-only">#</span>
              </div>
              {columns.map((c) => {
                const Icon = c.icon;
                const title = (
                  <>
                    {Icon && <Icon size={14} strokeWidth={1.6} aria-hidden="true" />}
                    <span className="sheet__th-label">{c.header}</span>
                  </>
                );
                return (
                  <div
                    key={c.id}
                    role="columnheader"
                    className={cellClass(c, "sheet__th")}
                    style={pinStyle(c)}
                    aria-sort={sortId === c.id ? "other" : undefined}
                  >
                    {c.sort ? (
                      <button
                        type="button"
                        className="sheet__sort"
                        aria-pressed={sortId === c.id}
                        onClick={() => setSortId(sortId === c.id ? null : c.id)}
                      >
                        {title}
                        <ArrowDownWideNarrow
                          className="sheet__sort-icon"
                          size={13}
                          strokeWidth={1.6}
                          aria-hidden="true"
                        />
                      </button>
                    ) : (
                      title
                    )}
                  </div>
                );
              })}
            </div>
          </div>
          <div role="rowgroup" className="sheet__body" ref={bodyRef}>
            {sorted.map((r, index) => {
              const id = ids[index];
              const selected = id === selectedId;
              return (
                <div
                  key={id}
                  role="row"
                  data-row-id={id}
                  tabIndex={id === tabStop ? 0 : -1}
                  aria-current={selected ? "true" : undefined}
                  className={`sheet__row sheet__row--body${selected ? " is-selected" : ""}`}
                  onClick={() => onOpen(r)}
                  onFocus={() => setFocusId(id)}
                  onKeyDown={(e) => onRowKeyDown(e, index)}
                >
                  <div role="cell" className="sheet__td sheet__rownum mono">
                    {index + 1}
                  </div>
                  {columns.map((c) => (
                    <div
                      key={c.id}
                      role="cell"
                      className={cellClass(c, "sheet__td")}
                      style={pinStyle(c)}
                    >
                      {c.cell(r)}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <ul className="data-table__stack" aria-label={label}>
        {sorted.map((r, index) => (
          <li key={ids[index]} data-row-id={ids[index]}>
            <button
              type="button"
              className={`data-table__stacked capsule capsule--interactive${ids[index] === selectedId ? " is-selected" : ""}`}
              onClick={() => onOpen(r)}
            >
              {stackedRow(r)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
