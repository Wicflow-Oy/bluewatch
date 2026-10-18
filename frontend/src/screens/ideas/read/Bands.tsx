// Potential and evidence as two separate three-step bands with a word, never a number. Potential that
// can't be judged yet is hatched across the whole scale: unknown, not zero.
import { ChevronDown, ShieldCheck } from "lucide-react";
import { useT } from "../../../i18n/messages";
import { vars } from "../../../lib/motion";
import type { EvidenceBand, IdeaAssessment, PotentialBand } from "../types";
import { readMessages } from "./messages";
import "./read.css";

type BandSource = Pick<
  IdeaAssessment,
  "potential" | "evidence" | "potential_rule" | "evidence_rule"
>;

/** How many of the three cells each band fills. */
const POTENTIAL_FILLED: Record<PotentialBand, number> = { high: 3, medium: 2, low: 1, unknown: 0 };
const EVIDENCE_FILLED: Record<EvidenceBand, number> = { strong: 3, some: 2, thin: 1 };

const POTENTIAL_TICKS = ["potential_low", "potential_medium", "potential_high"] as const;
const EVIDENCE_TICKS = ["evidence_thin", "evidence_some", "evidence_strong"] as const;

/** The two band boxes, the axiom under them and the two rules behind a disclosure. */
export function BandMeters({ read }: { read: BandSource }) {
  const { t } = useT(readMessages);
  return (
    <div className="ih-bands">
      <div className="ih-bands__pair">
        <BandMeter
          axis="potential"
          label={t("potential")}
          word={t(`potential_${read.potential}`)}
          filled={POTENTIAL_FILLED[read.potential]}
          unknown={read.potential === "unknown"}
          ticks={POTENTIAL_TICKS.map((key) => t(key))}
        />
        <BandMeter
          axis="evidence"
          label={t("evidence")}
          word={t(`evidence_${read.evidence}`)}
          filled={EVIDENCE_FILLED[read.evidence]}
          unknown={false}
          ticks={EVIDENCE_TICKS.map((key) => t(key))}
        />
      </div>
      <p className="callout callout--sea ih-bands__axiom">
        <ShieldCheck aria-hidden="true" />
        <span>{t("bandsCaption")}</span>
      </p>
      <details className="ih-disclosure ih-bands__rules">
        <summary>
          {t("howJudged")}
          <ChevronDown size={14} strokeWidth={1.75} aria-hidden="true" />
        </summary>
        <p>
          <strong>{t("potential")}.</strong> {read.potential_rule}
        </p>
        <p>
          <strong>{t("evidence")}.</strong> {read.evidence_rule}
        </p>
      </details>
    </div>
  );
}

interface BandMeterProps {
  axis: "potential" | "evidence";
  label: string;
  word: string;
  filled: number;
  unknown: boolean;
  ticks: string[];
}

function BandMeter({ axis, label, word, filled, unknown, ticks }: BandMeterProps) {
  const { t } = useT(readMessages);
  return (
    <div className={`ih-pm ih-pm--${axis}`}>
      <p className="ih-pm__label">{label}</p>
      <p className="ih-pm__word">{word}</p>
      <div
        className={`ih-pm__scale${unknown ? " ih-pm__scale--unknown" : ""}`}
        role="img"
        aria-label={t("bandSpoken", { axis: label, band: word })}
      >
        {[1, 2, 3].map((step) => (
          <i
            key={step}
            className={step <= filled ? "is-on" : undefined}
            style={vars({ "--j": step })}
          />
        ))}
      </div>
      <p className="ih-pm__ticks" aria-hidden="true">
        {ticks.map((tick) => (
          <span key={tick}>{tick}</span>
        ))}
      </p>
    </div>
  );
}

/** The same two bands as a small meter pair for a list row (keyed P/E) or a card (labelled). */
export function BandPills({ read, labelled = false }: { read: BandSource; labelled?: boolean }) {
  const { t } = useT(readMessages);
  const potential = t(`potential_${read.potential}`);
  const evidence = t(`evidence_${read.evidence}`);
  return (
    <span className={`ih-pills${labelled ? " ih-pills--labelled" : ""}`}>
      <Pill
        axis="potential"
        labelled={labelled}
        short={t("potential").charAt(0)}
        word={potential}
        full={t("pillPotential", { band: potential.toLocaleLowerCase() })}
        filled={POTENTIAL_FILLED[read.potential]}
        unknown={read.potential === "unknown"}
      />
      <Pill
        axis="evidence"
        labelled={labelled}
        short={t("evidence").charAt(0)}
        word={evidence}
        full={t("pillEvidence", { band: evidence.toLocaleLowerCase() })}
        filled={EVIDENCE_FILLED[read.evidence]}
        unknown={false}
      />
    </span>
  );
}

interface PillProps {
  axis: "potential" | "evidence";
  /** A card spells the axis out; a row shows its letter under a column header. */
  labelled: boolean;
  short: string;
  word: string;
  full: string;
  filled: number;
  unknown: boolean;
}

/** Screen readers always hear the full phrase ("Potential high"). */
function Pill({ axis, labelled, short, word, full, filled, unknown }: PillProps) {
  return (
    <span className={`ih-pill ih-pill--${axis}${unknown ? " ih-pill--unknown" : ""}`}>
      {!labelled && <span className="sr-only">{full}</span>}
      {!labelled && (
        <span className="ih-pill__key mono" aria-hidden="true">
          {short}
        </span>
      )}
      <span className="ih-pill__glyph" aria-hidden="true">
        {[1, 2, 3].map((step) => (
          <i key={step} className={step <= filled ? "is-on" : undefined} />
        ))}
      </span>
      <span className="ih-pill__word" aria-hidden={labelled ? undefined : "true"}>
        {labelled ? full : word}
      </span>
    </span>
  );
}
