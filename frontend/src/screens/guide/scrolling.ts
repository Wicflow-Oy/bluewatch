// Moving around a long page. The app routes on the URL hash, so in-page "#section" links would leave
// the guide; the table of contents scrolls with these instead.
import { useEffect, useState } from "react";

function behaviour(): ScrollBehavior {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

/** Scrolls a section's top into view and moves focus to its heading, so keyboard users land there too. */
export function scrollToSection(id: string): void {
  const section = document.getElementById(id);
  if (!section) return;
  section.scrollIntoView({ block: "start", behavior: behaviour() });
  section.querySelector<HTMLElement>("h3")?.focus({ preventScroll: true });
}

export function scrollToTop(): void {
  window.scrollTo({ top: 0, behavior: behaviour() });
}

/** How far down the screen a section's top must reach to count as the one being read. */
const READING_LINE = 0.3;

/** The section being read: the last one whose top has passed the reading line, or the last one at
 * the very bottom of the page, where short sections can never reach the line. */
function sectionInView(ids: readonly string[]): string | undefined {
  const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
  if (atBottom) return ids.at(-1);
  const line = window.innerHeight * READING_LINE;
  let current: string | undefined;
  for (const id of ids) {
    const top = document.getElementById(id)?.getBoundingClientRect().top;
    if (top !== undefined && top <= line) current = id;
  }
  return current;
}

export function useActiveSection(ids: readonly string[]): string | undefined {
  const [active, setActive] = useState<string>();

  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      setActive(sectionInView(ids));
    };
    const onScroll = () => {
      frame ||= requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(frame);
    };
  }, [ids]);

  return active;
}
