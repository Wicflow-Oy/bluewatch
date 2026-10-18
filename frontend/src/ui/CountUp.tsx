// A number that counts up to its value (ease-out quart), written straight to the DOM each frame.
import { useEffect, useEffectEvent, useRef, useState } from "react";
import { trunc } from "../lib/format";
import { prefersReducedMotion } from "../lib/motion";

interface CountUpProps {
  value: number;
  decimals?: number;
  duration?: number;
  delay?: number;
  /** Formats the number for display (default: trunc(v, decimals), which uses the language's decimal sign). */
  format?: (v: number) => string;
}

export function CountUp({ value, decimals = 2, duration = 900, delay = 0, format }: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const shown = useRef(prefersReducedMotion() ? value : 0);
  const fmt = (v: number) => (format ? format(v) : trunc(v, decimals));
  const [initial] = useState(() => fmt(shown.current));
  const paint = useEffectEvent((v: number) => {
    if (ref.current) ref.current.textContent = fmt(v);
  });

  useEffect(() => {
    if (prefersReducedMotion() || document.visibilityState !== "visible") {
      shown.current = value;
      paint(value);
      return;
    }
    const from = shown.current;
    const t0 = performance.now() + delay;
    let frame = requestAnimationFrame(function step(now) {
      const p = Math.min(1, Math.max(0, (now - t0) / duration));
      shown.current = p < 1 ? from + (value - from) * (1 - (1 - p) ** 4) : value; // ease-out quart
      paint(shown.current);
      if (p < 1) frame = requestAnimationFrame(step);
    });
    return () => cancelAnimationFrame(frame);
  }, [value, duration, delay]);

  return (
    <>
      <span ref={ref} aria-hidden="true">
        {initial}
      </span>
      <span className="sr-only">{fmt(value)}</span>
    </>
  );
}
