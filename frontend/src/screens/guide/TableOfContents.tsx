// "On this page": a sticky list beside the text on wider screens, a collapsible list above it on a phone.
// Both are rendered and the stylesheet shows one, so neither needs to know the screen size.
import { ChevronDown } from "lucide-react";
import { useEffect, useRef, type MouseEvent } from "react";
import { useT } from "../../i18n/messages";
import { href } from "../../lib/router";
import { guideMessages } from "./messages";
import { scrollToSection } from "./scrolling";

export interface TocEntry {
  id: string;
  title: string;
}

interface TocProps {
  track: string;
  entries: TocEntry[];
  active: string | undefined;
}

export function SideToc({ track, entries, active }: TocProps) {
  const { t } = useT(guideMessages);
  const navRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (navRef.current) keepInView(navRef.current);
  }, [active]);
  return (
    <nav ref={navRef} className="guide-toc guide-toc--side" aria-label={t("onThisPage")}>
      <p className="overline guide-toc__label">{t("onThisPage")}</p>
      <TocList track={track} entries={entries} active={active} />
    </nav>
  );
}

/** A long list scrolls inside its sticky frame; it follows the reader by keeping the current entry
 * in the middle (the browser clamps at either end, so the first entries keep their label above). */
function keepInView(nav: HTMLElement) {
  const link = nav.querySelector<HTMLElement>('[aria-current="location"]');
  if (link) nav.scrollTop = link.offsetTop - (nav.clientHeight - link.offsetHeight) / 2;
}

export function PhoneToc({ track, entries, active }: TocProps) {
  const { t } = useT(guideMessages);
  const detailsRef = useRef<HTMLDetailsElement>(null);
  return (
    <nav className="guide-toc guide-toc--phone" aria-label={t("onThisPage")}>
      <details ref={detailsRef}>
        <summary>
          <span>{t("onThisPage")}</span>
          <ChevronDown size={16} strokeWidth={1.5} aria-hidden="true" />
        </summary>
        <TocList
          track={track}
          entries={entries}
          active={active}
          onPick={() => detailsRef.current?.removeAttribute("open")}
        />
      </details>
    </nav>
  );
}

interface TocListProps extends TocProps {
  onPick?: () => void;
}

function TocList({ track, entries, active, onPick }: TocListProps) {
  // The link keeps the guide's own address, so opening it in a new tab still lands on this track.
  const go = (event: MouseEvent<HTMLAnchorElement>, id: string) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onPick?.();
    scrollToSection(id);
  };
  return (
    <ul className="guide-toc__list">
      {entries.map((entry) => (
        <li key={entry.id}>
          <a
            className="guide-toc__link"
            href={href({ name: "guide", track })}
            aria-current={entry.id === active ? "location" : undefined}
            onClick={(event) => go(event, entry.id)}
          >
            {entry.title}
          </a>
        </li>
      ))}
    </ul>
  );
}
