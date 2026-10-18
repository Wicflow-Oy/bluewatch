// The answer to a business ID: its register record and, when the API builds one, a compact card.
import { use } from "react";
import type { CardLookupResponse } from "../../api";
import { useT } from "../../i18n/messages";
import { LookupCard } from "../../ui/LookupCard";
import { LoadingRegion, Skeleton } from "../../ui/States";
import { companiesMessages } from "./messages";
import { NotAnswered } from "./NotAnswered";
import type { Settled } from "./useLookup";

interface CardResultProps {
  pending: Promise<Settled<CardLookupResponse>>;
  onRetry(): void;
}

export function CardResult({ pending, onRetry }: CardResultProps) {
  const outcome = use(pending);
  if (outcome.kind === "result")
    return <LookupCard result={outcome.data.lookup} card={outcome.data.card} />;
  return <NotAnswered outcome={outcome} what="lookup" onRetry={onRetry} />;
}

export function CardSkeleton() {
  const { t } = useT(companiesMessages);
  return (
    <LoadingRegion label={t("lookingUp")}>
      <div className="lookup-card">
        <Skeleton width={240} height={28} radius={6} />
        <Skeleton height={12} width="60%" />
        <Skeleton height={96} radius={8} />
      </div>
    </LoadingRegion>
  );
}
