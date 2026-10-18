// Potential and evidence as two separate capsule meters, each with the parts it is made of. They are
// never blended into one number.
import { ChevronDown, ShieldCheck } from "lucide-react";
import { useState } from "react";
import type { Mode } from "../../api";
import type { Score } from "../../contracts";
import { useT } from "../../i18n/messages";
import { floorTo, humanText, trunc } from "../../lib/format";
import { vars } from "../../lib/motion";
import { CountUp } from "../../ui/CountUp";
import { evidenceBand, potentialBand } from "../../ui/Meter";
import { uiMessages } from "../../ui/messages";
import { Panel } from "../../ui/Panel";
import { Tooltip } from "../../ui/Tooltip";
import { cardMessages } from "./messages";

type Kind = "potential" | "evidence";
type PartKey = (typeof PART_KEYS)[Kind][number];

const PART_KEYS = {
  potential: ["thesis_fit", "stage_fit", "venture_type", "traction_bonus"],
  evidence: ["coverage", "independence", "recency"],
} as const;

/** Traction is a bonus of at most +0.15, so its bar fills against that. */
const TRACTION_MAX = 0.15;

function isPartKey(key: string): key is PartKey {
  return [...PART_KEYS.potential, ...PART_KEYS.evidence].some((k) => k === key);
}

function Part({ name, value, index }: { name: string; value?: number; index: number }) {
  const { t } = useT(cardMessages);
  const label = isPartKey(name) ? t(`part_${name}`) : humanText(name);
  if (value === undefined) {
    return (
      <li className="parts__row parts__row--unknown" title={t("partUnknown")}>
        <span className="parts__label">{label}</span>
        <span className="parts__track" aria-hidden="true" />
        <span className="parts__value">—</span>
        <span className="sr-only">{t("partUnknown")}</span>
      </li>
    );
  }
  const bonus = name === "traction_bonus";
  const fill = Math.min(1, Math.max(0, bonus ? value / TRACTION_MAX : value));
  return (
    <li className="parts__row" style={vars({ "--i": index })}>
      <span className="parts__label">{label}</span>
      <span className="parts__track" aria-hidden="true">
        <span className="parts__fill" style={{ transform: `scaleX(${fill})` }} />
      </span>
      <span className="parts__value">
        {bonus ? "+" : ""}
        {trunc(value)}
      </span>
    </li>
  );
}

interface ScoreMeterProps {
  kind: Kind;
  value: number;
  parts: Record<string, number> | undefined;
  showValue: boolean;
}

/** The mockup's capsule meter: band word (Redstone: the value counting up), a pill track, then the parts. */
function ScoreMeter({ kind, value, parts = {}, showValue }: ScoreMeterProps) {
  const { t } = useT(cardMessages);
  const ui = useT(uiMessages);
  const label = t(kind);
  const band = kind === "potential" ? potentialBand(value) : evidenceBand(value);
  const clamped = Math.min(1, Math.max(0, value));
  const pct = floorTo(clamped * 100, 0);
  const extra = Object.keys(parts).filter((k) => !isPartKey(k));
  return (
    <div className={`meter meter--${kind} score-meter`}>
      <div className="meter__head">
        <Tooltip content={t(`${kind}Caption`)}>
          <span className="meter__label score-meter__label" tabIndex={0}>
            {label}
          </span>
        </Tooltip>
        <span className="meter__swatch" aria-hidden="true" />
      </div>
      {showValue ? (
        <p className="score-meter__figure">
          <span className="t-num">
            <CountUp value={floorTo(clamped, 2)} />
          </span>
          <span className="score-meter__band">{band}</span>
        </p>
      ) : (
        <p className="meter__band">{band}</p>
      )}
      <div
        className="meter__track"
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-valuetext={ui.t("meterSpoken", { band, pct })}
        title={`${label} ${trunc(clamped)}`}
      >
        <span className="meter__fill" style={{ width: `${pct}%` }} />
        <span className="meter__ticks" aria-hidden="true" />
      </div>
      <ul className="parts" aria-label={t(`${kind}Parts`)}>
        {[...PART_KEYS[kind], ...extra].map((key, i) => (
          <Part key={key} name={key} value={parts[key]} index={i} />
        ))}
      </ul>
    </div>
  );
}

/** The explanation lines in words. Redstone reads them first; A'Pelago gets them one click away. */
function HowWorkedOut({ lines, mode }: { lines: string[]; mode: Mode }) {
  const { t } = useT(cardMessages);
  const [open, setOpen] = useState(mode === "redstone");
  if (lines.length === 0) return null;
  return (
    <div className="worked-out">
      <button
        type="button"
        className="disclosure"
        aria-expanded={open}
        aria-controls="worked-out-body"
        onClick={() => setOpen((v) => !v)}
      >
        <ChevronDown size={14} strokeWidth={1.5} aria-hidden="true" />
        {t("howWorkedOut")}
      </button>
      {open && (
        <ul className="worked-out__list" id="worked-out-body">
          {lines.map((line) => (
            <li key={line}>{humanText(line)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ScorePanel({ score, mode }: { score: Score; mode: Mode }) {
  const { t } = useT(cardMessages);
  const redstone = mode === "redstone";
  return (
    <Panel
      title={t("potentialAndEvidence")}
      meta={<span className="vc-hint">{t("neverBlended")}</span>}
      className="score-panel"
    >
      <div className="dual">
        <ScoreMeter
          kind="potential"
          value={score.potential}
          parts={score.potential_parts}
          showValue={redstone}
        />
        <ScoreMeter
          kind="evidence"
          value={score.evidence}
          parts={score.evidence_parts}
          showValue={redstone}
        />
      </div>
      <p className="callout callout--sea score-panel__rule">
        <ShieldCheck size={16} strokeWidth={1.5} aria-hidden="true" />
        <Tooltip content={t("unknownsRuleTip")}>
          <span className="score-panel__rule-text" tabIndex={0}>
            {t("unknownsRule")}
          </span>
        </Tooltip>
      </p>
      <HowWorkedOut key={mode} lines={score.explanation ?? []} mode={mode} />
    </Panel>
  );
}
