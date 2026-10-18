// One very faint ring per pointer press, drawn on the canvas behind every card, like a quiet sonar ping in
// the water. Mounted once at the root of App.tsx. Nothing is created with reduced motion, in a hidden tab
// or for a secondary mouse button; the listener is passive, so scrolling is never affected.
import { useEffect, useRef } from "react";
import "./Shockwave.css";

const MAX_WAVES = 2; // each wave is a ring plus its echo: at most 4 rings alive

export function Shockwave() {
  const layerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onDown = (e: PointerEvent) => {
      const layer = layerRef.current;
      if (!layer || reduced.matches || document.visibilityState !== "visible" || !e.isPrimary)
        return;
      if (e.pointerType === "mouse" && e.button !== 0) return;
      while (layer.childElementCount >= MAX_WAVES) layer.firstElementChild?.remove();
      const wave = document.createElement("span");
      wave.className = "shock";
      wave.style.left = `${e.clientX}px`;
      wave.style.top = `${e.clientY}px`;
      const ring = document.createElement("span");
      ring.className = "shock__ring";
      const echo = document.createElement("span");
      echo.className = "shock__ring shock__ring--echo";
      wave.append(ring, echo);
      const remove = () => wave.remove();
      echo.addEventListener("animationend", remove, { once: true });
      window.setTimeout(remove, 1600); // safety net if animationend never fires
      layer.append(wave);
    };
    window.addEventListener("pointerdown", onDown, { passive: true, capture: true });
    return () => window.removeEventListener("pointerdown", onDown, { capture: true });
  }, []);

  return <div ref={layerRef} className="shockwave" aria-hidden="true" />;
}
