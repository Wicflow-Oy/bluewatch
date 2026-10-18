// The values each filter offers, in reading order and in the interface language, each counted against
// the other active filters.
import type { CompanyRow } from "../../contracts";
import { useLang } from "../../i18n/lang";
import { localeOf, useT } from "../../i18n/messages";
import { GROUP_ORDER, VERTICALS, verticalLabel } from "../../lib/labels";
import { useMeta } from "../../lib/meta";
import { resolutionChipMessages } from "../../ui/ResolutionChip.messages";
import { facetCounts, facetValue, LISTED, UNKNOWN, type FacetKey, type Selection } from "./filters";
import { companiesMessages } from "./messages";

export interface Option {
  value: string;
  label: string;
  count: number;
}

export interface FacetInput {
  rows: CompanyRow[];
  listedIds: Set<string>;
  text: string;
  selection: Selection;
}

const MATCHES: CompanyRow["resolution"][] = [
  "resolved",
  "probable",
  "ambiguous",
  "unconfirmed",
  "unresolved",
];

/** Returns a function from a facet to its options; values no row holds are left out. */
export function useFacetOptions({ rows, listedIds, text, selection }: FacetInput) {
  const { t } = useT(companiesMessages);
  const resolution = useT(resolutionChipMessages);
  const lang = useLang();
  const meta = useMeta();
  // The set spans more countries than the product names itself, so the browser names them.
  const regions = new Intl.DisplayNames([localeOf(lang)], { type: "region" });

  const labelled = (key: FacetKey, totals: Map<string, number>): [string, string][] => {
    switch (key) {
      case "country":
        // Most companies first; unknown last.
        return [...totals.keys()]
          .sort(
            (a, b) =>
              Number(a === UNKNOWN) - Number(b === UNKNOWN) ||
              (totals.get(b) ?? 0) - (totals.get(a) ?? 0),
          )
          .map((code) => [code, code === UNKNOWN ? t("unknown") : (regions.of(code) ?? code)]);
      case "group":
        return GROUP_ORDER.map((g) => [g, meta.group(g)]);
      case "vertical":
        return [
          ...VERTICALS.map((v): [string, string] => [v, verticalLabel(v)]),
          [UNKNOWN, t("unknown")],
        ];
      case "match":
        // The same words as the match chip on every card.
        return MATCHES.map((m) => [m, resolution.t(`state_${m}`)]);
      case "listed":
        return [[LISTED, t("onList")]];
    }
  };

  return (key: FacetKey): Option[] => {
    const totals = new Map<string, number>();
    for (const row of rows) {
      const value = facetValue(key, row, listedIds);
      totals.set(value, (totals.get(value) ?? 0) + 1);
    }
    const counts = facetCounts(rows, key, text, selection, listedIds);
    return labelled(key, totals)
      .filter(([value]) => totals.has(value))
      .map(([value, label]) => ({ value, label, count: counts.get(value) ?? 0 }));
  };
}
