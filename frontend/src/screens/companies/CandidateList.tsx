// The register search's answer to a name: every company it found, which registers answered, and a way
// to open one. An assessed company opens its card; any other is looked up in its register on the spot.
// Closed companies come last with their register status; forms read as plain words.
import { ChevronRight, TriangleAlert } from "lucide-react";
import { use } from "react";
import type { SearchCandidate, SearchResponse } from "../../api";
import { useLang } from "../../i18n/lang";
import { localeOf, useT } from "../../i18n/messages";
import { formatEventDate, registryLabel } from "../../lib/format";
import { href } from "../../lib/router";
import { Chip, CountryCode } from "../../ui/Chip";
import { RegisterStatusChip } from "../../ui/LookupCard";
import { SourceStatusPill } from "../../ui/SourceStatusPill";
import { EmptyState, LoadingRegion, Skeleton } from "../../ui/States";
import { companiesMessages } from "./messages";
import { NotAnswered } from "./NotAnswered";
import type { Settled } from "./useLookup";

type SearchSource = SearchResponse["sources"][number];

interface CandidateListProps {
  query: string;
  pending: Promise<Settled<SearchResponse>>;
  onPick(candidate: SearchCandidate): void;
  onRetry(): void;
}

export function CandidateList({ query, pending, onPick, onRetry }: CandidateListProps) {
  const { t, tn } = useT(companiesMessages);
  const outcome = use(pending);
  if (outcome.kind !== "result")
    return <NotAnswered outcome={outcome} what="search" onRetry={onRetry} />;
  const { candidates, sources, more } = outcome.data;
  // With live lookups off every register answers from recorded data, so a miss is not "no such company".
  const recordedOnly = sources.length > 0 && sources.every((s) => s.state === "cached");
  return (
    <div className="candidates">
      <div className="candidates__head">
        <p className="candidates__count" role="status">
          {candidates.length > 0
            ? tn("candidates", candidates.length, { query })
            : t(recordedOnly ? "noCandidatesRecorded" : "noCandidates", { query })}
        </p>
        <ul className="candidates__sources" aria-label={t("registersSearched")}>
          {sources.map((s) => (
            <li key={s.source}>
              <SourceStatusPill status={s} />
            </li>
          ))}
        </ul>
      </div>
      <SourcesDown sources={sources.filter((s) => s.state === "unavailable")} />
      {candidates.length === 0 ? (
        <EmptyState compact title={t(recordedOnly ? "recordedOnlyTitle" : "noCandidatesTitle")}>
          {recordedOnly ? `${t("recordedOnlyBody")} ${t("soleTraders")}` : t("soleTraders")}
        </EmptyState>
      ) : (
        <ul className="candidates__list">
          {candidates.map((c) => (
            <li key={`${c.country}:${c.business_id}:${c.company_id ?? ""}`}>
              <CandidateRow candidate={c} onPick={onPick} />
            </li>
          ))}
        </ul>
      )}
      {more && <p className="candidates__more">{t("moreCandidates", { n: candidates.length })}</p>}
    </div>
  );
}

/** A register that didn't answer may hold a match, so the list says so instead of looking complete. */
function SourcesDown({ sources }: { sources: SearchSource[] }) {
  const { tn } = useT(companiesMessages);
  const lang = useLang();
  if (sources.length === 0) return null;
  const names = new Intl.ListFormat(localeOf(lang), { type: "conjunction" }).format(
    sources.map((s) => s.label),
  );
  return (
    <p className="candidates__warning">
      <TriangleAlert size={14} strokeWidth={1.5} aria-hidden="true" />
      {tn("sourcesDown", sources.length, { sources: names })}
    </p>
  );
}

interface CandidateRowProps {
  candidate: SearchCandidate;
  onPick(candidate: SearchCandidate): void;
}

type MessageKey = keyof typeof companiesMessages.en;

/** Register form codes and PRH's English form names, by country, as plain words. */
const FORM_KEYS: Record<string, MessageKey> = {
  "FI:OY": "form_limited",
  "FI:OYJ": "form_public",
  "FI:Housing corporation": "form_housing",
  "FI:Mutual real estate limited company": "form_realEstate",
  "FI:Partnership": "form_partnership",
  "FI:Limited partnership": "form_limitedPartnership",
  "FI:Non-profit association": "form_association",
  "FI:Foundation": "form_foundation",
  "FI:Cooperative": "form_cooperative",
  "NO:AS": "form_limited",
  "NO:ASA": "form_public",
  "NO:NUF": "form_branch",
  "NO:UTLA": "form_foreign",
  "NO:ANS": "form_partnership",
  "NO:DA": "form_partnership",
  "NO:KS": "form_limitedPartnership",
  "NO:SA": "form_cooperative",
  "NO:FLI": "form_association",
  "NO:STI": "form_foundation",
  "NO:BRL": "form_housingCoop",
  "EE:OÜ": "form_limited",
  "EE:AS": "form_public",
  "EE:MTÜ": "form_association",
  "EE:SA": "form_foundation",
  "EE:TÜ": "form_cooperative",
};

function useFormLabel(country: string, form: string | null): string | null {
  const { t } = useT(companiesMessages);
  if (!form) return null;
  const key = FORM_KEYS[`${country}:${form}`];
  return key ? t(key) : form;
}

function CandidateRow({ candidate, onPick }: CandidateRowProps) {
  const { t } = useT(companiesMessages);
  const form = useFormLabel(candidate.country, candidate.form);
  const details = [form, candidate.municipality].filter(Boolean).join(" · ");
  const alias = candidate.formerly
    ? t("formerly", { name: candidate.formerly })
    : candidate.also_known_as && t("alsoKnownAs", { name: candidate.also_known_as });
  const body = (
    <>
      <CountryCode code={candidate.country} />
      <span className="candidate__main">
        <span className="candidate__name">{candidate.name}</span>
        {alias && <span className="candidate__alias">{alias}</span>}
        <span className="candidate__meta">
          <span className="mono">{registryLabel(candidate.country, candidate.business_id)}</span>
          {details && <span>{details}</span>}
          {candidate.registered && (
            <span>
              {t("registered", {
                date: formatEventDate(candidate.registered) ?? "",
              })}
            </span>
          )}
        </span>
      </span>
      <span className="candidate__end">
        {candidate.closed && <RegisterStatusChip status={candidate.status} />}
        {candidate.company_id ? (
          <Chip tone="teal" dot>
            {t("assessed")}
          </Chip>
        ) : (
          <ChevronRight size={16} strokeWidth={1.5} aria-hidden="true" className="candidate__go" />
        )}
      </span>
    </>
  );
  const className = candidate.closed ? "candidate candidate--closed" : "candidate";
  return candidate.company_id ? (
    <a className={className} href={href({ name: "companies", companyId: candidate.company_id })}>
      {body}
    </a>
  ) : (
    <button type="button" className={className} onClick={() => onPick(candidate)}>
      {body}
    </button>
  );
}

export function CandidatesSkeleton() {
  const { t } = useT(companiesMessages);
  return (
    <LoadingRegion label={t("searchingRegisters")}>
      <div className="candidates">
        <Skeleton width={200} height={14} />
        <ul className="candidates__list">
          {[0, 1, 2].map((i) => (
            <li key={i} className="candidate candidate--skeleton">
              <Skeleton width={24} height={18} />
              <span className="candidate__main">
                <Skeleton width={180} height={14} />
                <Skeleton width={260} height={12} />
              </span>
            </li>
          ))}
        </ul>
      </div>
    </LoadingRegion>
  );
}
