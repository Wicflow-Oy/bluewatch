// A small hover/focus tooltip rendered into <body>, so it is never clipped by a scrolling table or
// drawer. It is informational only (pointer-events: none); anything clickable lives in the trigger.
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import "./Tooltip.css";

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  placement?: "top" | "bottom" | "right";
  /** Stretch the trigger wrapper to its container (for block-level triggers). */
  block?: boolean;
}

const GAP = 8;
const EDGE = 8;
const HOVER_DELAY = 220;

export function Tooltip({ content, children, placement = "top", block = false }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const anchorRef = useRef<HTMLSpanElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);
  const timer = useRef<number | undefined>(undefined);
  const id = useId();

  const show = (delay: number) => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setOpen(true), delay);
  };
  const hide = () => {
    window.clearTimeout(timer.current);
    setOpen(false);
  };

  useEffect(() => () => window.clearTimeout(timer.current), []);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("scroll", close, true);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Position by writing to the element directly: measuring needs the rendered size first.
  useLayoutEffect(() => {
    const anchor = anchorRef.current;
    const tip = tipRef.current;
    if (!open || !anchor || !tip) return;
    const a = anchor.getBoundingClientRect();
    const t = tip.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let top: number;
    let left: number;
    if (placement === "right" && a.right + GAP + t.width < vw - EDGE) {
      top = a.top + a.height / 2 - t.height / 2;
      left = a.right + GAP;
    } else {
      const above = a.top - GAP - t.height;
      const below = a.bottom + GAP;
      const preferBelow = placement === "bottom" || above < EDGE;
      top = preferBelow && below + t.height < vh - EDGE ? below : Math.max(EDGE, above);
      left = a.left + a.width / 2 - t.width / 2;
    }
    left = Math.min(Math.max(EDGE, left), vw - t.width - EDGE);
    top = Math.min(Math.max(EDGE, top), vh - t.height - EDGE);
    // The entrance animation adds its own offset on top of --tip-xy.
    tip.style.setProperty("--tip-xy", `translate(${Math.round(left)}px, ${Math.round(top)}px)`);
    tip.style.transform = "var(--tip-xy)";
    tip.dataset.ready = "true";
  }, [open, placement]);

  return (
    <span
      ref={anchorRef}
      className={block ? "tip-anchor tip-anchor--block" : "tip-anchor"}
      aria-describedby={open ? id : undefined}
      onPointerEnter={(e) => e.pointerType === "mouse" && show(HOVER_DELAY)}
      onPointerLeave={hide}
      onFocus={() => show(0)}
      onBlur={hide}
    >
      {children}
      {open &&
        createPortal(
          <div ref={tipRef} id={id} role="tooltip" className="tooltip">
            {content}
          </div>,
          document.body,
        )}
    </span>
  );
}
