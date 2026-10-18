// The guide (#/guide, #/guide/<track>): a help centre beside the product that explains how BlueWatch
// and Idea Harbour work. It stands outside the app shell and reads in the interface language.
import { ArrowUp } from "lucide-react";
import { useEffect, useLayoutEffect, useMemo } from "react";
import { useLang } from "../../i18n/lang";
import { useT } from "../../i18n/messages";
import { formatDay } from "../../lib/format";
import { CONTENT_UPDATED, FAQ_TRACK, findTrack, guideContent, type GuideTrack } from "./content";
import { GuideHeader } from "./GuideHeader";
import { GuideHero } from "./GuideHero";
import { guideMessages } from "./messages";
import { Faq, FAQ_ID, Glossary, GLOSSARY_ID } from "./Reference";
import { scrollToTop, useActiveSection } from "./scrolling";
import { Section } from "./Section";
import { PhoneToc, SideToc, type TocEntry } from "./TableOfContents";
import "./guide.css";

export function GuideScreen({ track: trackId }: { track?: string }) {
  const { t } = useT(guideMessages);
  const lang = useLang();
  const content = guideContent(lang);
  const track = findTrack(content, trackId);
  const withFaq = track.id === FAQ_TRACK;

  const entries = useMemo<TocEntry[]>(
    () => [
      ...track.sections.map(({ id, title }) => ({ id, title })),
      ...(withFaq ? [{ id: FAQ_ID, title: t("faq") }] : []),
      { id: GLOSSARY_ID, title: t("glossary") },
    ],
    [track, withFaq, t],
  );
  const ids = useMemo(() => entries.map((entry) => entry.id), [entries]);
  const active = useActiveSection(ids);

  // The guide covers both workspaces, so it wears BlueWatch's own blue, not the last workspace's
  // accent. Before paint, so there is no flash of gold or red; the app sets its accent again on return.
  useLayoutEffect(() => {
    delete document.documentElement.dataset.workspace;
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [track.id]);

  return (
    <div className="guide">
      <GuideHeader />
      <GuideHero tracks={content.tracks} current={track.id} />
      <div className="guide-body">
        <aside className="guide-body__side">
          <SideToc track={track.id} entries={entries} active={active} />
        </aside>
        <main className="guide-article">
          <TrackIntro track={track} />
          <PhoneToc track={track.id} entries={entries} active={active} />
          {track.sections.map((section, i) => (
            <Section key={section.id} section={section} index={i} />
          ))}
          {withFaq && <Faq entries={content.faq} />}
          <Glossary entries={content.glossary} />
          <footer className="guide-footer">
            <span className="guide-footer__updated">
              {t("lastUpdated", { date: formatDay(CONTENT_UPDATED, { year: true }) })}
            </span>
            <button type="button" className="btn btn--subtle btn--sm" onClick={scrollToTop}>
              <ArrowUp size={14} strokeWidth={1.75} aria-hidden="true" />
              {t("backToTop")}
            </button>
          </footer>
        </main>
      </div>
    </div>
  );
}

function TrackIntro({ track }: { track: GuideTrack }) {
  return (
    <header className="guide-intro">
      <h2 className="guide-intro__title t-h1">{track.title}</h2>
      <p className="guide-intro__lead">{track.intro}</p>
    </header>
  );
}
