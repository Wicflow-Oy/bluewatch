// A pill segmented control with a sliding indicator: a radio group with roving focus.
import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { useSlidingIndicator } from "./useSlidingIndicator";
import "./Segmented.css";

export interface SegmentOption<T extends string> {
  value: T;
  label: ReactNode;
  count?: number;
  icon?: ReactNode;
  /** Accessible name when the label is an icon or an abbreviation. */
  ariaLabel?: string;
  /** Tooltip text (for icon-only segments). */
  title?: string;
  lang?: string;
  disabled?: boolean;
}

interface SegmentedProps<T extends string> {
  options: SegmentOption<T>[];
  value: T;
  onChange(value: T): void;
  /** The group's accessible name. */
  label: string;
  /** 26 / 30 / 34px segments. Default md. */
  size?: "sm" | "md" | "lg";
  /** White indicator (default) or ink indicator (nav, filters that act like nav). */
  tone?: "surface" | "ink";
  /** Full width, equal columns (phones, sheets). */
  block?: boolean;
  className?: string;
}

const NEXT: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
  size = "md",
  tone = "surface",
  block = false,
  className,
}: SegmentedProps<T>) {
  const itemsKey = options
    .map((o) => `${o.value}:${typeof o.label === "string" ? o.label : ""}`)
    .join("|");
  const { rootRef, indRef } = useSlidingIndicator<HTMLDivElement>(value, itemsKey);
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);

  function select(index: number) {
    const option = options[index];
    if (!option || option.disabled) return;
    buttons.current[index]?.focus();
    if (option.value !== value) onChange(option.value);
  }

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const current = options.findIndex((o) => o.value === value);
    const enabled = options.map((o, i) => (o.disabled ? -1 : i)).filter((i) => i >= 0);
    if (enabled.length === 0) return;
    let target: number | undefined;
    if (e.key === "Home") target = enabled[0];
    else if (e.key === "End") target = enabled[enabled.length - 1];
    else if (e.key in NEXT) {
      const pos = Math.max(0, enabled.indexOf(current));
      target = enabled[(pos + NEXT[e.key] + enabled.length) % enabled.length];
    }
    if (target === undefined) return;
    e.preventDefault();
    select(target);
  }

  const classes = [
    "seg",
    `seg--${size}`,
    tone === "ink" && "seg--ink",
    block && "seg--block",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      ref={rootRef}
      className={classes}
      role="radiogroup"
      aria-label={label}
      onKeyDown={onKeyDown}
    >
      <span className="seg__ind" ref={indRef} aria-hidden="true" />
      {options.map((o, i) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              buttons.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={on}
            aria-label={o.ariaLabel}
            title={o.title}
            lang={o.lang}
            disabled={o.disabled}
            tabIndex={on ? 0 : -1}
            data-selected={on}
            className="seg__btn"
            onClick={() => select(i)}
          >
            {o.icon}
            {o.label !== undefined && o.label !== null && o.label !== "" && <span>{o.label}</span>}
            {o.count !== undefined && <span className="seg__ct mono">{o.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
