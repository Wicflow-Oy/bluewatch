// "Look up any company": a business ID opens the company's register record and card; a name searches
// the Finnish, Norwegian and Estonian registers first and lets the user pick.
import { ArrowLeft, Search } from "lucide-react";
import { Suspense, useId } from "react";
import { useT } from "../../i18n/messages";
import { countryName } from "../../lib/labels";
import { Panel } from "../../ui/Panel";
import { Segmented } from "../../ui/Segmented";
import { CandidateList, CandidatesSkeleton } from "./CandidateList";
import { CardResult, CardSkeleton } from "./CardResult";
import { companiesMessages } from "./messages";
import type { LookupCountry } from "./query";
import type { Lookup } from "./useLookup";

const COUNTRIES: LookupCountry[] = ["any", "FI", "NO", "EE"];

export function LookupPanel({ lookup }: { lookup: Lookup }) {
  const { t } = useT(companiesMessages);
  const id = useId();
  const describedBy = lookup.problem ? `${id}-error ${id}-note` : `${id}-note`;
  return (
    <Panel
      title={t("lookupTitle")}
      icon={<Search size={16} strokeWidth={1.5} aria-hidden="true" />}
      className="lookup"
    >
      <form
        role="search"
        className="lookup__form"
        onSubmit={(e) => {
          e.preventDefault();
          lookup.submit();
        }}
      >
        <CountryPicker value={lookup.country} onChange={lookup.onCountry} />
        <label className="sr-only" htmlFor={`${id}-input`}>
          {t("nameOrId")}
        </label>
        <span className="lookup__field">
          <Search size={16} strokeWidth={1.5} aria-hidden="true" />
          <input
            id={`${id}-input`}
            className="input lookup__input"
            value={lookup.text}
            onChange={(e) => lookup.onText(e.target.value)}
            placeholder={
              lookup.country === "any" ? t("nameOrId") : t(`placeholder_${lookup.country}`)
            }
            autoComplete="off"
            spellCheck={false}
            aria-invalid={lookup.problem ? true : undefined}
            aria-describedby={describedBy}
          />
        </span>
        <button type="submit" className="btn btn--primary lookup__submit">
          {t("lookUp")}
        </button>
      </form>
      {lookup.problem && (
        <p className="lookup__error" id={`${id}-error`} role="alert">
          {t(`problem_${lookup.problem}`)}
        </p>
      )}
      <p className="lookup__note" id={`${id}-note`}>
        {t("privacyNote")}
      </p>
      <Results lookup={lookup} />
    </Panel>
  );
}

interface CountryPickerProps {
  value: LookupCountry;
  onChange(country: LookupCountry): void;
}

function CountryPicker({ value, onChange }: CountryPickerProps) {
  const { t } = useT(companiesMessages);
  return (
    <Segmented
      options={COUNTRIES.map((country) => ({
        value: country,
        label: country === "any" ? t("allCountries") : countryName(country),
      }))}
      value={value}
      onChange={onChange}
      label={t("facet_country")}
      className="lookup__countries"
    />
  );
}

function Results({ lookup }: { lookup: Lookup }) {
  const { t } = useT(companiesMessages);
  if (lookup.card)
    return (
      <div className="lookup__results">
        {lookup.search && (
          <button type="button" className="btn btn--ghost btn--sm" onClick={lookup.backToResults}>
            <ArrowLeft size={14} strokeWidth={1.5} aria-hidden="true" />
            {t("backToResults", { query: lookup.search.name })}
          </button>
        )}
        <Suspense fallback={<CardSkeleton />}>
          <CardResult pending={lookup.card} onRetry={lookup.retryCard} />
        </Suspense>
      </div>
    );
  if (lookup.search && lookup.searchResults)
    return (
      <div className="lookup__results">
        <Suspense fallback={<CandidatesSkeleton />}>
          <CandidateList
            query={lookup.search.name}
            pending={lookup.searchResults}
            onPick={lookup.pick}
            onRetry={lookup.retrySearch}
          />
        </Suspense>
      </div>
    );
  return null;
}
