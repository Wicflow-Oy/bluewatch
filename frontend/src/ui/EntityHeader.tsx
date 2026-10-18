// Who the company is, how sure we are of its register match, and its one-line description. Used by the
// venture card (drawer and full page) and by lookup results. On a phone the compact header keeps the
// name, ID and group in view and folds the rest under "Details".
import { ArrowUpRight, Check, ChevronDown, Copy } from "lucide-react";
import { useEffect, useState } from "react";
import type { Assessment, Company, Evidence, ListEntry } from "../contracts";
import { useT } from "../i18n/messages";
import { formatDay, humanText, registryLabel } from "../lib/format";
import { chipLabel, verticalText } from "../lib/labels";
import { Chip, CountryCode, GroupChip } from "./Chip";
import { entityHeaderMessages } from "./EntityHeader.messages";
import { ResolutionChip } from "./ResolutionChip";
import { SourceChip, sourceFromEvidence } from "./SourceChip";
import { useToast } from "./Toast";
import { Tooltip } from "./Tooltip";
import "./EntityHeader.css";

interface EntityHeaderProps {
  company: Company;
  assessment: Assessment;
  /** The list row, when the company is listed: adds the "Newly founded" style chip and the founding date. */
  entry?: ListEntry;
  /** Shown instead of the name; the register ID, website and municipality are hidden with it. */
  anonymisedName?: string;
  compact?: boolean;
  /** The card's evidence, so the one-liner can cite the row that makes the same claim. */
  evidence?: Evidence[];
}

const FLAGS = [
  "self_reported_only",
  "public_funding_dependency",
  "identity_not_confirmed",
  "no_technology_readiness",
  "pre_launch",
  "impact_claim_without_kpi",
  "too_late",
  "natural_person",
  "closed",
] as const;
type Flag = (typeof FLAGS)[number];
const AMBER_FLAGS: ReadonlySet<Flag> = new Set([
  "self_reported_only",
  "public_funding_dependency",
  "closed",
]);

function isFlag(flag: string): flag is Flag {
  return (FLAGS as readonly string[]).includes(flag);
}

function FlagChip({ flag }: { flag: string }) {
  const { t } = useT(entityHeaderMessages);
  if (!isFlag(flag)) {
    const words = humanText(flag);
    return <Chip>{words.charAt(0).toUpperCase() + words.slice(1)}</Chip>;
  }
  const chip = <Chip tone={AMBER_FLAGS.has(flag) ? "amber" : undefined}>{t(`flag_${flag}`)}</Chip>;
  if (flag !== "self_reported_only") return chip;
  return (
    <Tooltip content={t("selfReportedTip")}>
      <span className="entity__flag" tabIndex={0}>
        {chip}
      </span>
    </Tooltip>
  );
}

/** The copy-ID pill: on copy the icon slides out and a check slides in for a moment. */
function CopyIdPill({ id, label }: { id: string; label: string }) {
  const { t } = useT(entityHeaderMessages);
  const toast = useToast();
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (!done) return;
    const timer = window.setTimeout(() => setDone(false), 1600);
    return () => window.clearTimeout(timer);
  }, [done]);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(id);
      setDone(true);
    } catch {
      // No clipboard outside a secure context, or the browser refused it.
      toast(t("copyRefused", { id }));
    }
  };
  return (
    <Tooltip content={done ? t("copied") : t("copyId")}>
      <button
        type="button"
        className={`entity__copy mono${done ? " is-done" : ""}`}
        onClick={copy}
        aria-label={`${t("copyId")}: ${label}`}
      >
        <span>{label}</span>
        <span className="entity__copy-icon" aria-hidden="true">
          <Copy size={11} strokeWidth={1.75} />
          <Check size={11} strokeWidth={2.2} />
        </span>
        <span className="sr-only" aria-live="polite">
          {done ? t("copied") : ""}
        </span>
      </button>
    </Tooltip>
  );
}

function Founded({ date }: { date: string | null | undefined }) {
  const { t } = useT(entityHeaderMessages);
  if (!date) return <span>{t("foundingUnknown")}</span>;
  return (
    <span>
      {t("founded")} <span className="mono">{formatDay(date, { year: true })}</span>
    </span>
  );
}

function DetailsToggle({ open, onToggle }: { open: boolean; onToggle(): void }) {
  const { t } = useT(entityHeaderMessages);
  return (
    <button
      type="button"
      className="btn btn--ghost btn--sm entity__toggle"
      aria-expanded={open}
      onClick={onToggle}
    >
      {open ? t("less") : t("details")}
      <ChevronDown size={14} strokeWidth={1.5} aria-hidden="true" />
    </button>
  );
}

export function EntityHeader({
  company,
  assessment,
  entry,
  anonymisedName,
  compact = false,
  evidence,
}: EntityHeaderProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  const { registry } = company;
  const anonymous = anonymisedName !== undefined;
  const name =
    anonymisedName ??
    company.names[0] ??
    registry.name ??
    registryLabel(registry.country, registry.id);
  const vertical = verticalText(company.vertical ?? entry?.vertical ?? null, company.vertical_note);
  const website = company.domain ? (registry.website ?? `https://${company.domain}`) : null;
  const oneLinerEvidence = evidence?.find((e) => e.claim === company.one_liner);
  const oneLinerSource = oneLinerEvidence ? sourceFromEvidence(oneLinerEvidence) : null;
  const Name = compact ? "h2" : "h1";

  const idLabel = registryLabel(registry.country, registry.id);
  const tileTone = entry?.group === "act_now" ? " entity__tile--ink" : "";

  return (
    <header
      className={`entity${compact ? " entity--compact" : ""}${entry ? " entity--tiled" : ""}`}
    >
      {entry && (
        <span className={`entity__tile mono${tileTone}`} aria-hidden="true">
          {String(entry.rank).padStart(2, "0")}
        </span>
      )}
      <div className="entity__main">
        <div className="entity__name-row">
          <Name className="entity__name">{name}</Name>
          <GroupChip group={assessment.score.group} />
          {entry && <Chip>{chipLabel(entry.chip)}</Chip>}
        </div>

        <div className="entity__meta">
          <CountryCode code={registry.country} />
          {!anonymous &&
            (registry.id.trim() !== "" ? (
              <CopyIdPill id={registry.id} label={idLabel} />
            ) : (
              <span className="entity__id mono">{idLabel}</span>
            ))}
          {compact && (
            <DetailsToggle open={detailsOpen} onToggle={() => setDetailsOpen((open) => !open)} />
          )}
        </div>

        <div className={`entity__details${detailsOpen ? " entity__details--open" : ""}`}>
          <p className="entity__facts">
            {!anonymous && registry.municipality && <span>{registry.municipality}</span>}
            <Founded date={entry?.founded ?? registry.founded} />
            {vertical && <span>{vertical}</span>}
            {!anonymous && website && (
              <a href={website} target="_blank" rel="noopener noreferrer">
                {company.domain}
                <ArrowUpRight size={12} strokeWidth={1.75} aria-hidden="true" />
              </a>
            )}
          </p>

          <div className="entity__chips">
            <ResolutionChip resolution={company.resolution} />
            {(assessment.flags ?? []).map((flag) => (
              <FlagChip key={flag} flag={flag} />
            ))}
          </div>

          {company.one_liner && (
            <div className="entity__oneliner">
              <p className="entity__oneliner-text" title={company.one_liner}>
                {company.one_liner}
              </p>
              {oneLinerSource && <SourceChip source={oneLinerSource} />}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
