// What the company's own website says, claim by claim, each with the quote that was found on the page.
// Quotes stay in the page's own language: they are the evidence.
import { Check, Globe } from "lucide-react";
import { useId, useState } from "react";
import type { SiteRead } from "../api";
import type { Evidence } from "../contracts";
import { useT } from "../i18n/messages";
import { humanText } from "../lib/format";
import { lookupCardMessages } from "./LookupCard.messages";
import { SourceChip, sourceFromEvidence } from "./SourceChip";

const SHOWN = 4;

export function SiteClaims({ read, evidence }: { read: SiteRead; evidence: Evidence[] }) {
  const { t, tn } = useT(lookupCardMessages);
  const headingId = useId();
  const [all, setAll] = useState(false);
  const claims = evidence.filter(
    (e) => e.source_family === `site:${read.host}` && e.verified_quote && e.state === "fact",
  );
  const shown = all ? claims : claims.slice(0, SHOWN);
  return (
    <section className="site-claims" aria-labelledby={headingId}>
      <header className="site-claims__head">
        <h3 id={headingId} className="lookup-card__heading">
          <Globe size={14} strokeWidth={1.5} aria-hidden="true" />
          {t("siteHeading")}
        </h3>
        <p className="site-claims__by">
          <Check size={12} strokeWidth={2} aria-hidden="true" />
          {t("readBy", { host: read.host ?? "" })}
        </p>
        <p className="site-claims__found">
          {t(read.found_in_register ? "foundInRegister" : "foundByName")}
        </p>
      </header>
      <ul className="site-claims__list">
        {shown.map((e) => (
          <li key={e.id} className="site-claims__item">
            <p className="site-claims__claim">{humanText(e.claim)}</p>
            <p className="site-claims__quote">
              <q>{e.quote}</q>
            </p>
            <ClaimSource evidence={e} />
          </li>
        ))}
      </ul>
      {claims.length > shown.length && (
        <button type="button" className="btn btn--ghost btn--sm" onClick={() => setAll(true)}>
          {tn("moreClaims", claims.length - shown.length)}
        </button>
      )}
    </section>
  );
}

function ClaimSource({ evidence }: { evidence: Evidence }) {
  const source = sourceFromEvidence(evidence);
  return source ? <SourceChip source={source} /> : null;
}
