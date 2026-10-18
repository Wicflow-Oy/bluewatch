import { ArrowRight, BookOpen, Lightbulb, Waves, type LucideIcon } from "lucide-react";
import { useT } from "../../i18n/messages";
import { vars } from "../../lib/motion";
import { href } from "../../lib/router";
import type { GuideTrack } from "./content";
import { guideMessages } from "./messages";

const TRACK_ICONS: Record<string, LucideIcon> = { bluewatch: Waves, "idea-harbour": Lightbulb };

interface GuideHeroProps {
  tracks: GuideTrack[];
  current: string;
}

/** The page title, the two ways out to the product, and the switch between the guide's tracks. */
export function GuideHero({ tracks, current }: GuideHeroProps) {
  const { t } = useT(guideMessages);
  return (
    <div className="guide-hero">
      <div className="guide-hero__inner">
        <h1 className="guide-hero__title">{t("title")}</h1>
        <p className="guide-hero__subtitle">{t("subtitle")}</p>
        <div className="guide-hero__actions">
          <a className="btn btn--primary btn--lg" href={href({ name: "surfacing" })}>
            {t("openApp")}
          </a>
          <a className="btn btn--lg" href={href({ name: "apply" })}>
            {t("openStudentPage")}
          </a>
        </div>
        <nav className="guide-tracks" aria-label={t("tracks")}>
          {tracks.map((track, i) => (
            <TrackLink key={track.id} track={track} index={i} current={track.id === current} />
          ))}
        </nav>
      </div>
    </div>
  );
}

interface TrackLinkProps {
  track: GuideTrack;
  index: number;
  current: boolean;
}

function TrackLink({ track, index, current }: TrackLinkProps) {
  const Icon = TRACK_ICONS[track.id] ?? BookOpen;
  return (
    <a
      className="guide-track stagger-in"
      style={vars({ "--i": index + 2 })}
      href={href({ name: "guide", track: track.id })}
      aria-current={current ? "page" : undefined}
    >
      <span className="guide-track__icon" aria-hidden="true">
        <Icon size={18} strokeWidth={1.5} />
      </span>
      <span className="guide-track__title">{track.title}</span>
      <ArrowRight className="guide-track__go" size={14} strokeWidth={1.75} aria-hidden="true" />
    </a>
  );
}
