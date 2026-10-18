// "What we know": how many facts, assumptions and unknowns the card rests on, the ten checks, and the first
// lines of the ledger. The full ledger is one click away in the Evidence tab.
import { ArrowRight, Check } from "lucide-react";
import type { Evidence, VentureCard } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { useMeta } from "../../lib/meta";
import { vars } from "../../lib/motion";
import { CountUp } from "../../ui/CountUp";
import { gapLedgerMessages } from "../../ui/GapLedger.messages";
import { useLedgerFieldLabel } from "../../ui/GapLedger";
import { Panel } from "../../ui/Panel";
import { DimensionStrip } from "../../ui/Readiness";
import { SourceChip, sourceFromEvidence } from "../../ui/SourceChip";
import { cardMessages } from "./messages";

type State = "fact" | "assumption" | "unknown";

/** Lines of each kind shown here before "All in Evidence". */
const PREVIEW = 2;

function StateIcon({ state }: { state: State }) {
  return (
    <span className={`know-ic know-ic--${state}`} aria-hidden="true">
      {state === "fact" && <Check size={10} strokeWidth={2.5} />}
    </span>
  );
}

function Tally({
  facts,
  assumptions,
  unknowns,
}: Record<"facts" | "assumptions" | "unknowns", number>) {
  const ledger = useT(gapLedgerMessages);
  const cells: [State, number, string][] = [
    ["fact", facts, ledger.t("col_facts")],
    ["assumption", assumptions, ledger.t("col_assumptions")],
    ["unknown", unknowns, ledger.t("col_unknowns")],
  ];
  return (
    <ul className="tally">
      {cells.map(([state, n, label], i) => (
        <li key={state} className="tally__cell stagger-in" style={vars({ "--i": i })}>
          <b className="tally__n">
            <CountUp value={n} decimals={0} delay={120 + i * 60} />
          </b>
          <span className="tally__label">
            <StateIcon state={state} />
            {label}
          </span>
        </li>
      ))}
    </ul>
  );
}

function LedgerLine({ e, state }: { e: Evidence; state: State }) {
  const ledger = useT(gapLedgerMessages);
  const fieldLabel = useLedgerFieldLabel();
  const source = state === "unknown" ? null : sourceFromEvidence(e);
  const check = e.next_check;
  const how =
    state === "unknown"
      ? (check?.question ??
        (check?.how ? humanText(check.how) : e.why_unknown && humanText(e.why_unknown)))
      : null;
  return (
    <li className="know-line">
      <StateIcon state={state} />
      <div className="know-line__body">
        {state === "unknown" ? (
          <p className="know-line__text">
            <b>{fieldLabel(e.field)}</b>
            {how && <span className="know-line__how"> · {how}</span>}
          </p>
        ) : (
          <p className="know-line__text">{humanText(e.claim)}</p>
        )}
        {source && (
          <p className="know-line__meta">
            <SourceChip source={source} short />
          </p>
        )}
        {state === "assumption" && e.basis && (
          <p className="know-line__meta">{ledger.t("restsOn", { basis: humanText(e.basis) })}</p>
        )}
      </div>
    </li>
  );
}

function Section({ title, rows, state }: { title: string; rows: Evidence[]; state: State }) {
  if (rows.length === 0) return null;
  return (
    <section className="know-section">
      <h4 className="vc-subhead">
        <span>{title}</span>
        <span className="mono">{rows.length}</span>
      </h4>
      <ul className="know-lines">
        {rows.slice(0, PREVIEW).map((e) => (
          <LedgerLine key={e.id} e={e} state={state} />
        ))}
      </ul>
    </section>
  );
}

interface WhatWeKnowProps {
  card: VentureCard;
  onOpenEvidence(): void;
}

export function WhatWeKnow({ card, onOpenEvidence }: WhatWeKnowProps) {
  const { t } = useT(cardMessages);
  const ledger = useT(gapLedgerMessages);
  const meta = useMeta();
  const facts = card.ledger.facts ?? [];
  const assumptions = card.ledger.assumptions ?? [];
  const unknowns = card.ledger.unknowns ?? [];
  const { dimensions } = card.assessment;
  const sourced = dimensions.filter((d) => d.state === "fact").length;
  const total = facts.length + assumptions.length + unknowns.length;
  return (
    <Panel
      title={t("whatWeKnow")}
      meta={<span className="vc-hint">{t("whatWeKnowHint")}</span>}
      className="know"
    >
      <Tally facts={facts.length} assumptions={assumptions.length} unknowns={unknowns.length} />
      <h4 className="vc-subhead">
        <span>{t("tenDimensions")}</span>
        <span className="mono">{t("sourcedOf", { n: sourced, total: dimensions.length })}</span>
      </h4>
      <DimensionStrip dimensions={dimensions} labelFor={meta.dimension} />
      <Section title={ledger.t("col_facts")} rows={facts} state="fact" />
      <Section title={ledger.t("col_assumptions")} rows={assumptions} state="assumption" />
      <Section title={t("unknownsHow")} rows={unknowns} state="unknown" />
      {total > 0 && (
        <button type="button" className="btn btn--ghost btn--sm know__all" onClick={onOpenEvidence}>
          {t("allInEvidence", { n: total })}
          <ArrowRight size={14} strokeWidth={1.5} aria-hidden="true" />
        </button>
      )}
    </Panel>
  );
}
