// The BlueWatch mark: an eye on the waterline. Upper lid and iris above the line; below it, only the
// ripples of its reflection. Drawn in currentColor, so the ink tile inverts with the theme.
import "./Logo.css";

interface MarkProps {
  size?: number;
  /** Kept for existing callers; the line mark has no separate pupil animation. */
  animatePupil?: boolean;
  /** Kept for existing callers; the tile sets the colour through currentColor. */
  onTile?: boolean;
}

export function Mark({ size = 36 }: MarkProps) {
  return (
    <svg
      className="mark"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M4.5 17.25Q16 4.5 27.5 17.25"
        stroke="currentColor"
        strokeWidth="2.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M11.6 17.25a4.4 4.4 0 0 1 8.8 0Z" fill="currentColor" />
      <circle className="mark__iris" cx="17.7" cy="15" r="1.15" />
      <path d="M2.5 17.25h27" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" />
      <path
        d="M10.5 21.4h11M13.5 25h5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        opacity=".45"
      />
    </svg>
  );
}

/** The app tile: the ink pill colour with the mark at 69%; in Graphite it turns light with a dark mark. */
export function AppTile({ size = 36 }: { size?: number }) {
  return (
    <span
      className="app-tile"
      style={{ width: size, height: size, borderRadius: Math.round(size * 0.3125) }}
    >
      <Mark size={Math.round(size * 0.69)} />
    </span>
  );
}

export function Wordmark({ name }: { name: string }) {
  return <span className="wordmark">{name}</span>;
}
