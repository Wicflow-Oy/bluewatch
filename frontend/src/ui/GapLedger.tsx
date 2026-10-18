// The gap ledger: what is a fact (with its source), what is an assumption (with what it rests on), what is
// unknown (with how it gets closed) and what does not apply. Missing information is a lead, so every
// unknown ends in a next check.
import { Check, ChevronDown, MessageSquareText, RefreshCw } from "lucide-react";
import { useState } from "react";
import type { Evidence, GapLedger as Ledger } from "../contracts";
import { useT } from "../i18n/messages";
import { formatDay, humanText } from "../lib/format";
import { useMeta } from "../lib/meta";
import { Chip } from "./Chip";
import { Deadline } from "./Deadline";
import { gapLedgerMessages } from "./GapLedger.messages";
import { SourceChip, sourceFromEvidence, type SourceRef } from "./SourceChip";
import "./GapLedger.css";

type ColumnKey = "facts" | "assumptions" | "unknowns" | "not_applicable";
type Cite = { source: SourceRef; index: number };

const COLUMNS: { key: ColumnKey; state: NonNullable<Evidence["state"]> }[] = [
  { key: "facts", state: "fact" },
  { key: "assumptions", state: "assumption" },
  { key: "unknowns", state: "unknown" },
  { key: "not_applicable", state: "not_applicable" },
];

const STANDARD_FIELDS = ["product", "customers", "team", "funding", "public_contracts"] as const;
type StandardField = (typeof STANDARD_FIELDS)[number];

function isStandardField(field: string): field is StandardField {
  return (STANDARD_FIELDS as readonly string[]).includes(field);
}

/** The ledger field in words: the five standard checks and the ten dimensions are translated, any other
 *  key reads as words. */
export function useLedgerFieldLabel(): (field: string) => string {
  const { t } = useT(gapLedgerMessages);
  const { dimension } = useMeta();
  return (field) => {
    if (isStandardField(field)) return t(`field_${field}`);
    const label = dimension(field);
    return label === field ? humanText(field) : label;
  };
}

/** Numbered sources, counted across the whole ledger: [1] [2] … in reading order. */
function numberSources(ledger: Ledger): Map<string, Cite> {
  const cited = new Map<string, Cite>();
  const candidates = [...(ledger.facts ?? []), ...(ledger.assumptions ?? []).filter((e) => e.url)];
  for (const e of candidates) {
    const source = sourceFromEvidence(e);
    if (source) cited.set(e.id, { source, index: cited.size + 1 });
  }
  return cited;
}

function Claim({ text, cite }: { text: string; cite?: Cite }) {
  return (
    <p className="ledger__claim">
      {humanText(text)}
      {cite && (
        <>
          {" "}
          <SourceChip source={cite.source} index={cite.index} />
        </>
      )}
    </p>
  );
}

function FactItem({ e, cite }: { e: Evidence; cite?: Cite }) {
  const { t } = useT(gapLedgerMessages);
  return (
    <>
      <Claim text={e.claim} cite={cite} />
      {e.quote && (
        <p className="ledger__quote">
          <q>{e.quote}</q>
          {e.verified_quote && (
            <span className="ledger__checked">
              <Check size={12} strokeWidth={2} aria-hidden="true" />
              {t("quoteChecked")}
            </span>
          )}
        </p>
      )}
      {e.confirmed_by && (
        <Chip tone="teal" dot>
          {t("confirmedByCompany")} · <span className="mono">{formatDay(e.confirmed_by.at)}</span>
        </Chip>
      )}
    </>
  );
}

function AssumptionItem({ e, cite }: { e: Evidence; cite?: Cite }) {
  const { t } = useT(gapLedgerMessages);
  return (
    <>
      <Claim text={e.claim} cite={cite} />
      {e.basis && <p className="ledger__sub">{t("restsOn", { basis: humanText(e.basis) })}</p>}
    </>
  );
}

function UnknownItem({ e, today }: { e: Evidence; today: string }) {
  const { t } = useT(gapLedgerMessages);
  const fieldLabel = useLedgerFieldLabel();
  const check = e.next_check;
  return (
    <>
      <p className="overline ledger__field">{fieldLabel(e.field)}</p>
      {e.why_unknown && <p className="ledger__claim">{humanText(e.why_unknown)}</p>}
      {check?.kind === "ask_founder" && check.question && (
        <p className="ledger__check">
          <MessageSquareText size={14} strokeWidth={1.5} aria-hidden="true" />
          <span>
            {t("askCompany")}: <q>{check.question}</q>
          </span>
        </p>
      )}
      {check?.kind === "public_check" && check.how && (
        <p className="ledger__check">
          <RefreshCw size={14} strokeWidth={1.5} aria-hidden="true" />
          <span>{t("weCheck", { how: humanText(check.how) })}</span>
        </p>
      )}
      {check?.kind === "public_check" && check.question && (
        <p className="ledger__check ledger__check--alt">
          <span>
            {t("orAsk")}: <q>{check.question}</q>
          </span>
        </p>
      )}
      {check?.due && (
        <p className="ledger__sub">
          {t("due")} <Deadline date={check.due} today={today} />
        </p>
      )}
    </>
  );
}

function NotApplicableItem({ e }: { e: Evidence }) {
  return (
    <>
      <Claim text={e.claim} />
      {e.why_unknown && <p className="ledger__sub">{humanText(e.why_unknown)}</p>}
    </>
  );
}

function LedgerItem({ column, e, cite }: { column: ColumnKey; e: Evidence; cite?: Cite }) {
  const { today } = useMeta();
  switch (column) {
    case "facts":
      return <FactItem e={e} cite={cite} />;
    case "assumptions":
      return <AssumptionItem e={e} cite={cite} />;
    case "unknowns":
      return <UnknownItem e={e} today={today} />;
    case "not_applicable":
      return <NotApplicableItem e={e} />;
  }
}

function ColumnHead({ state, title, count }: { state: string; title: string; count: number }) {
  return (
    <>
      <span className={`ledger__swatch ledger__swatch--${state}`} aria-hidden="true" />
      <span className="ledger__title">{title}</span>
      <span className="ledger__count mono">{count}</span>
    </>
  );
}

interface ColumnProps {
  column: ColumnKey;
  state: string;
  rows: Evidence[];
  listId: string;
  cited: Map<string, Cite>;
  /** Stacked layout only: whether the section is open, and how to fold it. */
  toggle?: { open: boolean; onToggle(): void };
}

function LedgerColumn({ column, state, rows, listId, cited, toggle }: ColumnProps) {
  const { t } = useT(gapLedgerMessages);
  const title = t(`col_${column}`);
  const head = <ColumnHead state={state} title={title} count={rows.length} />;
  const expanded = toggle?.open ?? true;
  return (
    <section className={`ledger__col ledger__col--${state}`}>
      {toggle ? (
        <h3 className="ledger__head-wrap">
          <button
            type="button"
            className="ledger__head ledger__head--toggle"
            aria-expanded={toggle.open}
            aria-controls={listId}
            onClick={toggle.onToggle}
          >
            {head}
            <ChevronDown
              size={16}
              strokeWidth={1.5}
              className="ledger__chevron"
              aria-hidden="true"
            />
          </button>
        </h3>
      ) : (
        <h3 className="ledger__head">{head}</h3>
      )}
      {expanded &&
        (rows.length === 0 ? (
          <p className="ledger__none" id={listId}>
            {t("none")}
          </p>
        ) : (
          <ul className="ledger__items" id={listId}>
            {rows.map((e) => (
              <li key={e.id} className="ledger__item">
                <LedgerItem column={column} e={e} cite={cited.get(e.id)} />
              </li>
            ))}
          </ul>
        ))}
    </section>
  );
}

interface GapLedgerProps {
  ledger: Ledger;
  /** columns: four side by side (full page; they stack on narrow screens). stacked: folding sections. */
  layout: "columns" | "stacked";
}

export function GapLedger({ ledger, layout }: GapLedgerProps) {
  const cited = numberSources(ledger);
  // Stacked, the unknowns open first: they are the next step.
  const [open, setOpen] = useState<Set<ColumnKey>>(() => new Set(["unknowns"]));

  const toggle = (key: ColumnKey) =>
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <div className={`ledger ledger--${layout}`}>
      <div className="ledger__grid">
        {COLUMNS.map(({ key, state }) => (
          <LedgerColumn
            key={key}
            column={key}
            state={state}
            rows={ledger[key] ?? []}
            listId={`ledger-${ledger.company_id}-${key}`.replace(/[^A-Za-z0-9-]/g, "-")}
            cited={cited}
            toggle={
              layout === "stacked"
                ? { open: open.has(key), onToggle: () => toggle(key) }
                : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}
