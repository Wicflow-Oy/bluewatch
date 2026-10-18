// The state behind "Look up any company": what was typed, the register search it started and the company
// picked from it. Everything lives in this component's memory; a reload forgets it.
import { useState } from "react";
import type { Country, SearchCandidate } from "../../api";
import { askOnce, lookupCard, searchCompanies, type Outcome } from "../../data";
import { useLang } from "../../i18n/lang";
import { usePreset } from "../../lib/preset";
import { useWorkspace } from "../../lib/workspace";
import { parseQuery, type LookupCountry, type QueryProblem } from "./query";

/** An outcome, or an unexpected failure shown as a failed lookup instead of a broken page. */
export type Settled<T> = Outcome<T> | { kind: "failed" };

interface CardTarget {
  country: Country;
  businessId: string;
}

interface Search {
  name: string;
  within: LookupCountry;
}

function settle<T>(pending: Promise<Outcome<T>>): Promise<Settled<T>> {
  return pending.catch((): Settled<T> => ({ kind: "failed" }));
}

function asLookupCountry(country: string): Country | null {
  return country === "FI" || country === "NO" || country === "EE" ? country : null;
}

export function useLookup() {
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const lang = useLang();
  const [text, setText] = useState("");
  const [country, setCountry] = useState<LookupCountry>("any");
  const [problem, setProblem] = useState<QueryProblem | null>(null);
  const [search, setSearch] = useState<Search | null>(null);
  const [target, setTarget] = useState<CardTarget | null>(null);

  // Both answers carry prose in the interface language, so a language switch asks again; so does a
  // retry, which sets a fresh search or target object. askOnce sends each question once, however
  // often React renders before it shows the answer.
  const searchResults =
    search &&
    askOnce(search, lang, () =>
      settle(searchCompanies(search.name, search.within === "any" ? undefined : search.within)),
    );
  // The card also follows the workspace and preset.
  const card =
    target &&
    askOnce(target, `${lang}:${mode}:${preset}`, () =>
      settle(lookupCard(target.country, target.businessId, mode, preset)),
    );

  const run = (raw: string, within: LookupCountry) => {
    const parsed = parseQuery(raw, within);
    if (parsed.kind === "invalid") {
      setProblem(parsed.problem);
      return;
    }
    setProblem(null);
    if (parsed.kind === "name") {
      setTarget(null);
      setSearch({ name: parsed.name, within });
    } else {
      setSearch(null);
      setTarget({ country: parsed.country, businessId: parsed.businessId });
    }
  };

  return {
    text,
    country,
    problem,
    search,
    searchResults,
    card,
    onText: (value: string) => {
      setText(value);
      setProblem(null);
    },
    onCountry: setCountry,
    submit: () => run(text, country),
    /** From the table: nothing assessed matched, so look the same name or ID up in the registers. */
    lookUp: (typed: string) => {
      setText(typed);
      setCountry("any");
      run(typed, "any");
    },
    pick: (candidate: SearchCandidate) => {
      const candidateCountry = asLookupCountry(candidate.country);
      if (candidateCountry && candidate.business_id)
        setTarget({ country: candidateCountry, businessId: candidate.business_id });
    },
    backToResults: () => setTarget(null),
    retrySearch: () => search && setSearch({ ...search }),
    retryCard: () => target && setTarget({ ...target }),
  };
}

export type Lookup = ReturnType<typeof useLookup>;
