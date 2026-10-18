// Every claim carries one of these. Hover or focus shows the three dates that make a claim checkable:
// when it happened, when we first saw it, and when we last retrieved it.
import { ArrowUpRight, Link2Off } from "lucide-react";
import type { Evidence, Reason } from "../contracts";
import { useT } from "../i18n/messages";
import { formatEventDate, hostOf } from "../lib/format";
import { evidenceSourceLabel } from "../lib/labels";
import { uiMessages } from "./messages";
import { Tooltip } from "./Tooltip";
import "./SourceChip.css";

export interface SourceRef {
  label: string;
  url?: string | null;
  event?: string | null;
  firstSeen?: string | null;
  retrieved?: string | null;
  deadline?: string | null;
  quoteChecked?: boolean;
}

export function sourceFromReason(r: Reason): SourceRef {
  return {
    label: r.source_label,
    url: r.url,
    event: r.event_date,
    firstSeen: r.first_seen_at,
    retrieved: r.retrieved_at,
  };
}

/** null for a gap-ledger entry, which gets no chip. */
export function sourceFromEvidence(e: Evidence): SourceRef | null {
  const label = evidenceSourceLabel(e);
  if (label === null) return null;
  return {
    label,
    url: e.url,
    event: e.event_date,
    firstSeen: e.first_seen_at,
    retrieved: e.retrieved_at,
    quoteChecked: e.verified_quote,
  };
}

function DateRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="tooltip__row">
      <dt>{label}</dt>
      <dd>{formatEventDate(value) ?? "—"}</dd>
    </div>
  );
}

/** "Company site (oceanbox.io)" -> "oceanbox.io"; "EU public tenders (TED)" -> "TED"; register names -> their code. */
export function shortSource(label: string): string {
  const m = /\(([^)]+)\)\s*$/.exec(label);
  return m ? m[1] : label;
}

/** Registers and EU records get the sea-green number. */
export function isRegistrySource(label: string): boolean {
  return /register|\(TED\)|Brreg|PRH|RIK|SCB|CORDIS/i.test(label);
}

interface SourceChipProps {
  source: SourceRef;
  index?: number;
  /** Row use: a short label and no trailing link icon. */
  short?: boolean;
}

export function SourceChip({ source, index, short = false }: SourceChipProps) {
  const { t } = useT(uiMessages);
  const host = hostOf(source.url);
  const details = (
    <>
      <div className="tooltip__title">{source.label}</div>
      <dl className="source-tip__dates">
        <DateRow label={t("dateEvent")} value={source.event} />
        <DateRow label={t("dateFirstSeen")} value={source.firstSeen} />
        <DateRow label={t("dateRetrieved")} value={source.retrieved} />
        {source.deadline && <DateRow label={t("dateDeadline")} value={source.deadline} />}
      </dl>
      <p className="tooltip__note">
        {source.quoteChecked && `${t("quoteChecked")} `}
        {host ? t("opensHost", { host }) : t("noPublicLink")}
      </p>
    </>
  );
  const body = (
    <>
      {index !== undefined && (
        <span className="source-chip__index mono" aria-hidden="true">
          {index}
        </span>
      )}
      <span className="source-chip__label">{short ? shortSource(source.label) : source.label}</span>
      {short ? null : source.url ? (
        <ArrowUpRight size={12} strokeWidth={1.75} aria-hidden="true" />
      ) : (
        <Link2Off size={12} strokeWidth={1.75} aria-hidden="true" />
      )}
    </>
  );
  const srDates = [
    source.event && t("srEvent", { date: formatEventDate(source.event) ?? "" }),
    source.firstSeen && t("srFirstSeen", { date: formatEventDate(source.firstSeen) ?? "" }),
    source.retrieved && t("srRetrieved", { date: formatEventDate(source.retrieved) ?? "" }),
  ]
    .filter(Boolean)
    .join(", ");

  const classes = [
    "source-chip",
    short && "source-chip--short",
    index === undefined && "source-chip--plain",
    isRegistrySource(source.label) && "source-chip--registry",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Tooltip content={details}>
      {source.url ? (
        <a className={classes} href={source.url} target="_blank" rel="noopener noreferrer">
          {body}
          <span className="sr-only">
            {t("srSourceLink", { label: source.label, dates: srDates ? `, ${srDates}` : "" })}
          </span>
        </a>
      ) : (
        <span className={`${classes} source-chip--nolink`} tabIndex={0}>
          {body}
          <span className="sr-only">{t("srSourceNoLink", { label: source.label })}</span>
        </span>
      )}
    </Tooltip>
  );
}
