// A lookup or register search that came back without an answer: the API's refusal in its own words, or
// a retry when the service didn't answer.
import { RefreshCw, TriangleAlert } from "lucide-react";
import { useT } from "../../i18n/messages";
import { ErrorState } from "../../ui/States";
import { companiesMessages } from "./messages";
import type { Settled } from "./useLookup";

interface NotAnsweredProps {
  outcome: Exclude<Settled<unknown>, { kind: "result" }>;
  /** What didn't finish, for the title. */
  what: "lookup" | "search";
  onRetry(): void;
}

export function NotAnswered({ outcome, what, onRetry }: NotAnsweredProps) {
  const { t } = useT(companiesMessages);
  if (outcome.kind === "rejected")
    return (
      <p className="lookup__error" role="alert">
        {outcome.message}
      </p>
    );
  return (
    <div className="lookup__unavailable">
      <ErrorState
        compact
        icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={
          outcome.kind === "unavailable"
            ? t("partUnavailable")
            : t(what === "lookup" ? "lookupDidntFinish" : "searchDidntFinish")
        }
        action={
          <button type="button" className="btn btn--sm" onClick={onRetry}>
            <RefreshCw size={14} strokeWidth={1.5} aria-hidden="true" />
            {t("tryAgain")}
          </button>
        }
      >
        {t("notAnsweredBody")}
      </ErrorState>
    </div>
  );
}
