// A score made of parts, each drawn against its own ceiling, so every point (and every missing point) is
// visible. The bar's segments are as wide as each part's maximum: the weighting is part of the picture.
import { useT } from "../i18n/messages";
import { floorTo, ofN } from "../lib/format";
import { uiMessages } from "./messages";
import "./ScoreBar.css";
import { CountUp } from "./CountUp";

export interface ScorePart {
  key: string;
  label: string;
  value: number;
  max: number;
}

interface ScoreBarProps {
  parts: ScorePart[];
  max: 100;
  total: number;
}

interface CompactScoreBarProps {
  max: 100;
  total: number;
  /** The accessible name, such as "Promise score 87 of 100". */
  label: string;
}

/** Whole points, floored: a part at 17.9 shows 17, never 18. */
const points = (value: number) => floorTo(value, 0);

function Fill({ value, max }: { value: number; max: number }) {
  const share = max > 0 ? Math.min(1, value / max) : 0;
  return <span className="score-bar__fill" style={{ width: `${share * 100}%` }} />;
}

/** Only a 64 px bar of the total, for list rows: too narrow for the parts, so the row's number carries them. */
export function CompactScoreBar({ max, total, label }: CompactScoreBarProps) {
  return (
    <span className="score-bar score-bar--compact" role="img" aria-label={label}>
      <span className="score-bar__track" aria-hidden="true">
        <span className="score-bar__segment">
          <Fill value={total} max={max} />
        </span>
      </span>
    </span>
  );
}

export function ScoreBar({ parts, max, total }: ScoreBarProps) {
  const { t } = useT(uiMessages);
  return (
    <div className="score-bar">
      <p className="score-bar__total">
        <span className="score-bar__total-value mono">
          <CountUp value={total} decimals={0} />
        </span>
        <span className="score-bar__total-max mono">{t("outOf", { n: max })}</span>
      </p>
      <span className="score-bar__track" aria-hidden="true">
        {parts.map((part) => (
          <span key={part.key} className="score-bar__segment" style={{ flexGrow: part.max }}>
            <Fill value={part.value} max={part.max} />
          </span>
        ))}
      </span>
      <dl className="score-bar__parts">
        {parts.map((part) => (
          <div key={part.key} className="score-bar__part">
            <dt>{part.label}</dt>
            <dd className="score-bar__part-track" aria-hidden="true">
              <Fill value={part.value} max={part.max} />
            </dd>
            <dd className="score-bar__part-value mono">
              {ofN(points(part.value), points(part.max))}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
