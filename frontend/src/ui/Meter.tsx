// Potential and evidence are two separate meters. The evidence track is hatched where it is empty:
// that space is unknowns, which lower evidence and never potential.
import type { ReactNode } from "react";
import { translator, useT } from "../i18n/messages";
import { floorTo, trunc } from "../lib/format";
import { uiMessages } from "./messages";
import "./Meter.css";

export function potentialBand(v: number): string {
  const { t } = translator(uiMessages);
  return t(
    v >= 0.8
      ? "potentialHigh"
      : v >= 0.65
        ? "potentialMediumHigh"
        : v >= 0.5
          ? "potentialMedium"
          : "potentialLow",
  );
}

export function evidenceBand(v: number): string {
  const { t } = translator(uiMessages);
  return t(v >= 0.5 ? "evidenceSolid" : v >= 0.35 ? "evidencePartial" : "evidenceThin");
}

interface MeterProps {
  label: string;
  value: number;
  band: string;
  kind: "potential" | "evidence";
  caption?: ReactNode;
  /** Print the value (floored to 2 decimals) beside the band word. */
  showValue?: boolean;
}

export function Meter({ label, value, band, kind, caption, showValue = false }: MeterProps) {
  const { t } = useT(uiMessages);
  const clamped = Math.min(1, Math.max(0, value));
  // Floored like every figure in the product: 0.975 fills 97 of 100, never 98.
  const pct = floorTo(clamped * 100, 0);
  return (
    <div className={`meter meter--${kind}`}>
      <div className="meter__head">
        <span className="meter__label">{label}</span>
        <span className="meter__swatch" aria-hidden="true" />
      </div>
      <p className="meter__band">
        {band}
        {showValue && <span className="meter__value mono">{trunc(clamped)}</span>}
      </p>
      <div
        className="meter__track"
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-valuetext={t("meterSpoken", { band, pct })}
        title={`${label} ${trunc(clamped)}`}
      >
        <span className="meter__fill" style={{ width: `${pct}%` }} />
        <span className="meter__ticks" aria-hidden="true" />
      </div>
      {caption && <p className="meter__caption">{caption}</p>}
    </div>
  );
}

interface MiniMeterProps {
  kind: "potential" | "evidence";
  value: number;
  /** Accessible name, e.g. "Potential 0.95". */
  label: string;
}

/** The P/E line for rows and tables (mockup .mini): key letter, a 4px track, the floored value. */
export function MiniMeter({ kind, value, label }: MiniMeterProps) {
  const { t } = useT(uiMessages);
  const clamped = Math.min(1, Math.max(0, value));
  const pct = floorTo(clamped * 100, 0);
  return (
    <span
      className={`mini-meter mini-meter--${kind}`}
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
    >
      <span className="mini-meter__key" aria-hidden="true">
        {t(kind === "potential" ? "miniKeyPotential" : "miniKeyEvidence")}
      </span>
      <span className="mini-meter__track" aria-hidden="true">
        <span className="mini-meter__fill" style={{ transform: `scaleX(${pct / 100})` }} />
      </span>
      <span className="mini-meter__value" aria-hidden="true">
        {trunc(clamped)}
      </span>
    </span>
  );
}
