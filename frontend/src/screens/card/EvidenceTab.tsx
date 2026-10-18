import type { VentureCard } from "../../contracts";
import { useT } from "../../i18n/messages";
import { GapLedger } from "../../ui/GapLedger";
import { SourceStatusPill } from "../../ui/SourceStatusPill";
import { cardMessages } from "./messages";

export function EvidenceTab({ card, layout }: { card: VentureCard; layout: "drawer" | "page" }) {
  const { t } = useT(cardMessages);
  const sources = card.sources ?? [];
  return (
    <div className="card-stack">
      <p className="card-intro">{t("evidenceIntro")}</p>
      <GapLedger ledger={card.ledger} layout={layout === "page" ? "columns" : "stacked"} />
      {sources.length > 0 && (
        <div className="card-sources">
          <span className="overline">{t("sourcesBehind")}</span>
          <div className="card-sources__pills">
            {sources.map((s) => (
              <SourceStatusPill key={s.source} status={s} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
