// One filter as a pop-over menu of checkable options, and the option list it shares with the phone sheet.
import { Check, ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Option } from "./facetOptions";

interface OptionListProps {
  options: Option[];
  isOn(value: string): boolean;
  onToggle(value: string): void;
}

export function OptionList({ options, isOn, onToggle }: OptionListProps) {
  return (
    <ul className="filter-options">
      {options.map((o) => (
        <li key={o.value}>
          <button
            type="button"
            className="filter-option press"
            aria-pressed={isOn(o.value)}
            onClick={() => onToggle(o.value)}
          >
            <span className="filter-option__box" aria-hidden="true">
              <Check size={11} strokeWidth={2.5} />
            </span>
            <span className="filter-option__label">{o.label}</span>
            <span className="filter-option__count mono">{o.count}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Closes on a click outside or Escape. */
function useDismiss(open: boolean, setOpen: (open: boolean) => void) {
  const rootRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (e.target instanceof Node && !rootRef.current?.contains(e.target)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, setOpen]);
  return rootRef;
}

interface FacetMenuProps extends OptionListProps {
  label: string;
  selected: number;
}

export function FacetMenu({ label, selected, ...list }: FacetMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useDismiss(open, setOpen);
  return (
    <div className="facet-menu" ref={rootRef}>
      <button
        type="button"
        className="chip-btn facet-menu__trigger"
        aria-expanded={open}
        aria-pressed={selected > 0}
        onClick={() => setOpen(!open)}
      >
        {label}
        {selected > 0 && <span className="ct">{selected}</span>}
        <ChevronDown size={14} strokeWidth={1.5} aria-hidden="true" />
      </button>
      {open && (
        <div className="facet-menu__pop" role="group" aria-label={label}>
          <OptionList {...list} />
        </div>
      )}
    </div>
  );
}
