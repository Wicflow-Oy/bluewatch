// The reference parts at the end of a track: questions people ask, and the words the product uses.
import { ChevronDown } from "lucide-react";
import { useMemo } from "react";
import { useLang } from "../../i18n/lang";
import { localeOf, useT } from "../../i18n/messages";
import type { FaqEntry, GlossaryEntry } from "./content";
import { guideMessages } from "./messages";
import { SectionFrame } from "./Section";

export const FAQ_ID = "faq";
export const GLOSSARY_ID = "glossary";

export function Faq({ entries }: { entries: FaqEntry[] }) {
  const { t } = useT(guideMessages);
  return (
    <SectionFrame id={FAQ_ID} title={t("faq")}>
      <div className="guide-faq">
        {entries.map((entry) => (
          <details key={entry.q} className="guide-faq__item inset">
            <summary>
              <span>{entry.q}</span>
              <ChevronDown size={16} strokeWidth={1.5} aria-hidden="true" />
            </summary>
            <p className="guide-text">{entry.a}</p>
          </details>
        ))}
      </div>
    </SectionFrame>
  );
}

/** Terms in each language's alphabetical order, since translation reorders them. */
export function Glossary({ entries }: { entries: GlossaryEntry[] }) {
  const { t } = useT(guideMessages);
  const lang = useLang();
  const sorted = useMemo(
    () => [...entries].sort((a, b) => a.term.localeCompare(b.term, localeOf(lang))),
    [entries, lang],
  );
  return (
    <SectionFrame id={GLOSSARY_ID} title={t("glossary")}>
      <dl className="guide-glossary inset">
        {sorted.map((entry) => (
          <div key={entry.term} className="guide-glossary__entry">
            <dt>{entry.term}</dt>
            <dd>{entry.definition}</dd>
          </div>
        ))}
      </dl>
    </SectionFrame>
  );
}
