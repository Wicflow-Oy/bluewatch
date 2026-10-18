// Values one page hands to the next (search to Founder view and Funding, a card or a bridge to
// Outreach). They live in this module's memory only, never in the URL or storage, because some of
// them are what a visitor typed.
//
// The receiving page reads its value with a hook and the value is cleared once that page has mounted,
// so a later visit starts clean. It is not cleared on the first read: React can render a page more
// than once before it shows it (a render that waits on data is thrown away and redone), and a value
// cleared during a thrown-away render would be lost.
import { useEffect, useState } from "react";
import type { Country } from "../api";

export interface FounderPrefill {
  country: Country;
  businessId: string;
}

export interface OutreachTarget {
  companyId: string;
  bridgeId?: string;
}

let founderPrefill: FounderPrefill | null = null;
let outreachTarget: OutreachTarget | null = null;
let fundingFocus: string | null = null;

const clearFounderPrefill = () => {
  founderPrefill = null;
};
const clearOutreachTarget = () => {
  outreachTarget = null;
};
const clearFundingFocus = () => {
  fundingFocus = null;
};

/** The value as the page first rendered it; cleared from memory once the page has mounted. */
function useHandedOver<T>(read: () => T | null, clear: () => void): T | null {
  const [value] = useState(read);
  useEffect(() => clear(), [clear]);
  return value;
}

export function setFounderPrefill(prefill: FounderPrefill): void {
  founderPrefill = prefill;
}

export function useFounderPrefill(): FounderPrefill | null {
  return useHandedOver(() => founderPrefill, clearFounderPrefill);
}

export function setOutreachTarget(target: OutreachTarget): void {
  outreachTarget = target;
}

export function useOutreachTarget(): OutreachTarget | null {
  return useHandedOver(() => outreachTarget, clearOutreachTarget);
}

/** The funding instrument to highlight when Funding opens (an instrument id from the API). */
export function setFundingFocus(instrumentId: string): void {
  fundingFocus = instrumentId;
}

export function useFundingFocus(): string | null {
  return useHandedOver(() => fundingFocus, clearFundingFocus);
}
