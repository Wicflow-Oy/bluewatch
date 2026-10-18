// A sheet under the top bar: a right-hand side sheet (default), the large centred venture-card sheet, or a
// small bottom sheet. Phones show every variant as a bottom sheet. It traps Tab while open, closes on Escape
// or the scrim, and gives focus back to whatever opened it.
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { isMorphing } from "../lib/motion";
import "./Drawer.css";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  label: string;
  children: ReactNode;
  /** "side": right sheet (default, the old drawer). "card": the large centred venture-card sheet that a row
   *  morphs into. "sheet": a bottom sheet with auto height (More, alerts on phones). */
  variant?: "side" | "card" | "sheet";
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

export function Drawer({ open, onClose, label, children, variant = "side" }: DrawerProps) {
  // Stay mounted while the closing animation plays, unless a view transition animates the exit.
  const [mounted, setMounted] = useState(open);
  if (open && !mounted) setMounted(true);
  if (!open && mounted && isMorphing()) setMounted(false);

  const panelRef = useRef<HTMLElement>(null);
  const returnTo = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    returnTo.current = document.activeElement as HTMLElement | null;
    panel?.focus({ preventScroll: true });
    return () => {
      // Another layer may already have moved focus; only restore it if nobody has.
      const active = document.activeElement;
      if (!active || active === document.body || panel?.contains(active)) {
        returnTo.current?.focus?.({ preventScroll: true });
      }
    };
  }, [open]);

  // The top bar stays usable above a sheet, so Escape must also close it when focus is up there.
  // Popovers and the palette stop their own Escape before it reaches the window.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape" && !panelRef.current?.contains(e.target as Node)) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!mounted) return null;

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === "Escape") {
      e.stopPropagation();
      onClose();
      return;
    }
    if (e.key !== "Tab" || !panelRef.current) return;
    const items = [...panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
      (el) => el.offsetParent !== null,
    );
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (
      e.shiftKey &&
      (document.activeElement === first || document.activeElement === panelRef.current)
    ) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  return createPortal(
    <div className="drawer-root" data-state={open ? "open" : "closing"}>
      <div className="drawer-scrim" onClick={onClose} aria-hidden="true" />
      <aside
        ref={panelRef}
        className="drawer"
        data-variant={variant}
        data-sheet-panel=""
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        onKeyDown={onKeyDown}
        onAnimationEnd={(e) => {
          if (!open && e.target === e.currentTarget) setMounted(false);
        }}
      >
        {children}
      </aside>
    </div>,
    document.body,
  );
}
