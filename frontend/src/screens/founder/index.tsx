// Founder view: any FI, NO or EE business ID → funding tiers, programmes, investors and the next 30
// days. What the visitor types stays in memory (this screen and its lookup hook): never the URL,
// storage or logs.
import { Lock } from "lucide-react";
import { useState } from "react";
import type { Country } from "../../api";
import { useT } from "../../i18n/messages";
import { useFounderPrefill } from "../../lib/handoff";
import { useMeta } from "../../lib/meta";
import { shellMessages } from "../../shell/messages";
import { IdInput } from "../../ui/IdInput";
import { PageHeader, Panel } from "../../ui/Panel";
import type { Comparison } from "./compare";
import { FounderResult } from "./FounderResult";
import { founderMessages } from "./messages";
import { LookupFailed, RegisterDown, ResultPreview, ResultSkeleton } from "./ResultStates";
import { useFounderLookup, type Answer } from "./useFounderLookup";
import "./founder.css";

export function FounderScreen() {
  const { t } = useT(founderMessages);
  const shell = useT(shellMessages);
  // A business ID handed over by search, read once on mount (memory only).
  const prefill = useFounderPrefill();
  const [country, setCountry] = useState<Country>(prefill?.country ?? "FI");
  const [value, setValue] = useState(prefill?.businessId ?? "");
  const lookup = useFounderLookup(prefill);

  return (
    <div className="page founder">
      <PageHeader title={shell.t("page_founder")} explainer={t("explainer")} />
      <div className="founder__top">
        <Panel className="founder__lookup" title={t("lookUpTitle")}>
          <IdInput
            country={country}
            value={value}
            onCountry={(next) => {
              setCountry(next);
              lookup.clearRefusal();
            }}
            onChange={(next) => {
              setValue(next);
              lookup.clearRefusal();
            }}
            onSubmit={() => lookup.run({ country, businessId: value })}
            busy={lookup.busy}
            error={lookup.refusal && t(`refusal_${lookup.refusal}`)}
          />
        </Panel>
        <PrivacyNote />
      </div>
      {lookup.busy ? (
        <ResultSkeleton />
      ) : (
        <Result answer={lookup.answer} comparison={lookup.comparison} onRetry={lookup.retry} />
      )}
    </div>
  );
}

interface ResultProps {
  answer: Answer | null;
  comparison: Comparison | null;
  onRetry(): void;
}

function Result({ answer, comparison, onRetry }: ResultProps) {
  const meta = useMeta();
  if (answer === null) return <ResultPreview />;
  if (answer.kind === "failed") return <LookupFailed onRetry={onRetry} />;
  if (answer.kind === "unavailable") {
    return <RegisterDown country={answer.country} onRetry={onRetry} />;
  }
  return (
    <FounderResult
      response={answer.response}
      recorded={answer.origin === "demo"}
      comparison={comparison}
      mode={meta.mode}
      today={meta.today}
      onRetry={onRetry}
    />
  );
}

/** The privacy promise: a panel beside the input on wide screens, one expandable line on a phone. */
function PrivacyNote() {
  const { t } = useT(founderMessages);
  const lines = [t("privacyStored"), t("privacyRegister"), t("privacySoleTraders")];
  return (
    <>
      <Panel className="founder__privacy" title={t("privacyTitle")}>
        <ul className="founder__privacy-lines">
          {lines.map((line) => (
            <li key={line}>
              <Lock size={16} strokeWidth={1.5} aria-hidden="true" />
              {line}
            </li>
          ))}
        </ul>
      </Panel>
      <details className="founder__privacy-compact">
        <summary>
          <Lock size={16} strokeWidth={1.5} aria-hidden="true" />
          {lines[0]}
        </summary>
        <ul className="founder__privacy-lines">
          {lines.slice(1).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </details>
    </>
  );
}
