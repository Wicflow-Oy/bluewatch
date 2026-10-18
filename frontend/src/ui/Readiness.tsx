import type { DimensionState } from "../contracts";
import { useT } from "../i18n/messages";
import { humanText } from "../lib/format";
import { vars } from "../lib/motion";
import { uiMessages } from "./messages";
import { Tooltip } from "./Tooltip";
import "./Readiness.css";

/** "1-3" -> [1, 3]; anything else (a word, null) -> null. */
export function parseBand(band: string | null | undefined): [number, number] | null {
  const m = /^(\d+)\s*[-–]\s*(\d+)$/.exec(band ?? "");
  return m ? [Number(m[1]), Number(m[2])] : null;
}

interface TrackProps {
  max: number;
  level?: number | null;
  band?: string | null;
  showNumbers: boolean;
  label: string;
}

/**
 * One cell per level. Reached levels are solid, the band we can't narrow down is a softer fill,
 * and an unknown level is hatched across the whole track (never drawn as zero).
 */
export function ReadinessTrack({ max, level, band, showNumbers, label }: TrackProps) {
  const { t } = useT(uiMessages);
  const range = parseBand(band);
  const known = level != null || range !== null;
  const cells = Array.from({ length: max }, (_, i) => {
    const n = i + 1;
    if (!known) return "unknown";
    if (level != null) return n <= level ? "reached" : range && n <= range[1] ? "band" : "empty";
    if (range && n < range[0]) return "reached";
    if (range && n <= range[1]) return "band";
    return "empty";
  });
  const spoken = !known
    ? t("levelUnknown")
    : level != null
      ? t("levelOf", { level, max })
      : t("levelBetween", { low: range?.[0] ?? "", high: range?.[1] ?? "", max });
  return (
    <div
      className={`track${known ? "" : " track--unknown"}${showNumbers ? " track--numbers" : ""}`}
      role="img"
      aria-label={`${label}: ${spoken}`}
    >
      {cells.map((state, i) => (
        <span key={i} className={`track__cell track__cell--${state}`} style={vars({ "--j": i })}>
          {showNumbers && <span className="track__n mono">{i + 1}</span>}
        </span>
      ))}
    </div>
  );
}

export function ConfidenceDots({
  confidence,
}: {
  confidence: "low" | "medium" | "high" | undefined;
}) {
  const { t } = useT(uiMessages);
  const filled = confidence === "high" ? 3 : confidence === "medium" ? 2 : 1;
  const spoken = t(`confidence_${confidence ?? "low"}`);
  return (
    <span className="confidence" title={spoken}>
      {[1, 2, 3].map((n) => (
        <span
          key={n}
          className={n <= filled ? "confidence__dot confidence__dot--on" : "confidence__dot"}
        />
      ))}
      <span className="sr-only">{spoken}</span>
    </span>
  );
}

export function DimensionStrip({
  dimensions,
  labelFor,
}: {
  dimensions: DimensionState[];
  labelFor: (key: string) => string;
}) {
  const { t } = useT(uiMessages);
  const stateLabel = (state: DimensionState["state"]) => t(`state_${state}`);
  const counts = dimensions.reduce<Record<string, number>>((acc, d) => {
    acc[d.state] = (acc[d.state] ?? 0) + 1;
    return acc;
  }, {});
  return (
    <div className="dimensions">
      <ul className="dimensions__cells" aria-label={t("tenDimensions")}>
        {dimensions.map((d) => (
          <li key={d.key}>
            <Tooltip
              block
              content={
                <>
                  <div className="tooltip__title">{labelFor(d.key)}</div>
                  <p className="muted">
                    {stateLabel(d.state)}
                    {d.note ? `: ${humanText(d.note)}` : ""}
                  </p>
                </>
              }
            >
              <span
                className={`dimension dimension--${d.state}`}
                data-state-label={stateLabel(d.state)}
                tabIndex={0}
              >
                <span className="dimension__label">{labelFor(d.key)}</span>
                <span className="sr-only">{`: ${stateLabel(d.state)}`}</span>
              </span>
            </Tooltip>
          </li>
        ))}
      </ul>
      <p className="dimensions__legend">
        {(["fact", "assumption", "unknown", "not_applicable"] as const)
          .filter((s) => counts[s])
          .map((s) => (
            <span key={s} className="dimensions__key">
              <span className={`dimensions__swatch dimension--${s}`} aria-hidden="true" />
              {stateLabel(s)} <span className="mono">{counts[s]}</span>
            </span>
          ))}
      </p>
    </div>
  );
}
