// The founder lookup's lifecycle: one request at a time from the visitor's point of view, the latest
// answer wins, and the previous company's tiers are kept in memory for the comparison strip. What the
// visitor typed lives only in this hook's refs and state: never the URL, storage or logs.
import { useCallback, useEffect, useRef, useState } from "react";
import type { Country, FounderResponse } from "../../api";
import type { FounderTier } from "../../contracts";
import { lookupFounder, type Origin } from "../../data";
import { useLang } from "../../i18n/lang";
import { registryLabel } from "../../lib/format";
import { tierChanges, type Comparison } from "./compare";

export interface Submitted {
  country: Country;
  businessId: string;
}

export type Answer =
  | { kind: "response"; response: FounderResponse; origin: Origin }
  /** No API and no recorded answer for this ID. */
  | { kind: "unavailable"; country: Country }
  | { kind: "failed" };

/** Why the ID was refused before any result: shown under the input, not in place of the result. */
export type Refusal = "checkDigit" | "rateLimited";

type Settled = Answer | { kind: "refused"; refusal: Refusal };

/** The last company that had a view. */
interface Previous {
  id: string;
  name: string;
  country: string;
  tiers: FounderTier[];
}

async function ask(next: Submitted): Promise<Settled> {
  try {
    const outcome = await lookupFounder(next.country, next.businessId);
    if (outcome.kind === "result") {
      return { kind: "response", response: outcome.data, origin: outcome.origin };
    }
    if (outcome.kind === "unavailable") return { kind: "unavailable", country: next.country };
    // The format already passed in the browser, so the API refuses only a wrong check digit (422)
    // or a visitor over the rate limit (429).
    return { kind: "refused", refusal: outcome.status === 429 ? "rateLimited" : "checkDigit" };
  } catch {
    return { kind: "failed" };
  }
}

function previousOf(response: FounderResponse): Previous | null {
  const view = response.view;
  if (!view) return null;
  const { profile } = view;
  return {
    id: profile.id,
    name: profile.name ?? registryLabel(profile.country, profile.business_id ?? ""),
    country: profile.country,
    tiers: view.tiers ?? [],
  };
}

export function useFounderLookup(prefill: Submitted | null) {
  const [busy, setBusy] = useState(prefill !== null);
  const [refusal, setRefusal] = useState<Refusal | null>(null);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const submitted = useRef<Submitted | null>(null);
  const previous = useRef<Previous | null>(null);
  const latest = useRef(0);

  const remember = useCallback((response: FounderResponse) => {
    const next = previousOf(response);
    if (!next) return;
    const before = previous.current;
    if (before && before.id !== next.id) {
      setComparison({
        name: before.name,
        country: before.country,
        changes: tierChanges(before.tiers, next.tiers),
        total: next.tiers.length,
      });
    }
    previous.current = next;
  }, []);

  /** Sends a lookup; a slower earlier one must never overwrite a later answer. */
  const send = useCallback(
    (next: Submitted) => {
      const ticket = ++latest.current;
      submitted.current = next;
      void ask(next).then((settled) => {
        if (ticket !== latest.current) return;
        setBusy(false);
        if (settled.kind === "refused") {
          setRefusal(settled.refusal);
          return;
        }
        if (settled.kind === "response") remember(settled.response);
        setAnswer(settled);
      });
    },
    [remember],
  );

  const run = useCallback(
    (next: Submitted) => {
      setBusy(true);
      setRefusal(null);
      send(next);
    },
    [send],
  );

  // A prefill starts busy, so the effect only sends.
  useEffect(() => {
    if (prefill) send(prefill);
  }, [prefill, send]);

  // The rules' prose comes back in the language of the request: ask again after a switch, keeping the
  // current answer on screen until the new one arrives.
  const lang = useLang();
  const askedIn = useRef(lang);
  useEffect(() => {
    if (askedIn.current === lang) return;
    askedIn.current = lang;
    if (submitted.current) send(submitted.current);
  }, [lang, send]);

  const retry = useCallback(() => {
    if (submitted.current) run(submitted.current);
  }, [run]);

  const clearRefusal = useCallback(() => setRefusal(null), []);

  return { busy, refusal, answer, comparison, run, retry, clearRefusal };
}
