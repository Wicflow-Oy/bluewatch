import { FilePenLine, ShieldAlert } from "lucide-react";
import type { Resolution, VentureCard } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText, registryLabel } from "../../lib/format";
import { setOutreachTarget } from "../../lib/handoff";
import { pageHref } from "../../lib/router";
import { shellMessages } from "../../shell/messages";
import { useLedgerFieldLabel } from "../../ui/GapLedger";
import { Panel } from "../../ui/Panel";
import { cardMessages } from "./messages";

const MAX_QUESTIONS = 4;

interface BlockedProps {
  card: VentureCard;
  state: Exclude<Resolution["state"], "resolved">;
}

/** Not an error: the desk only writes to a company whose register match is certain. */
function Blocked({ card, state }: BlockedProps) {
  const { t } = useT(cardMessages);
  const { names, registry, resolution } = card.company;
  const name = names[0] ?? registry.name ?? registryLabel(registry.country, registry.id);
  return (
    <section
      className="callout callout--amber outreach-blocked"
      aria-labelledby="outreach-blocked-title"
    >
      <span className="outreach-blocked__icon">
        <ShieldAlert size={20} strokeWidth={1.5} aria-hidden="true" />
      </span>
      <div className="outreach-blocked__text">
        <h3 className="outreach-blocked__title" id="outreach-blocked-title">
          {t("blockedTitle")}
        </h3>
        <p className="outreach-blocked__body">
          {t(`match_${state}`, { name, reason: humanText(resolution.reason) })} {t("blockedNext")}
        </p>
      </div>
    </section>
  );
}

function AskTheCompany({ card }: { card: VentureCard }) {
  const { t, tn } = useT(cardMessages);
  const shell = useT(shellMessages);
  const fieldLabel = useLedgerFieldLabel();
  const askable = (card.ledger.unknowns ?? []).filter((u) => u.next_check?.question);
  const topBridge = card.bridges?.[0];
  return (
    <Panel title={t("askTitle")}>
      <div className="ask">
        <p className="ask__lead">
          {askable.length > 0 ? tn("askable", askable.length) : t("nothingToAsk")}
        </p>
        {askable.length > 0 && (
          <ul className="ask__list">
            {askable.slice(0, MAX_QUESTIONS).map((u) => (
              <li key={u.id} className="ask__item inset">
                <span className="overline">{fieldLabel(u.field)}</span>
                <q>{u.next_check?.question}</q>
              </li>
            ))}
          </ul>
        )}
        <p className="ask__note">{t("deskNote")}</p>
        <div className="ask__action">
          <a
            className="btn btn--primary btn--lg"
            href={pageHref("outreach")}
            onClick={() =>
              setOutreachTarget({ companyId: card.company.id, bridgeId: topBridge?.id })
            }
          >
            <FilePenLine size={16} strokeWidth={1.5} aria-hidden="true" />
            {t("prepareRequest")}
          </a>
          <p className="ask__fine">
            {t("personApproves")} {shell.t("sendingOff")}.
          </p>
        </div>
      </div>
    </Panel>
  );
}

export function OutreachTab({ card }: { card: VentureCard }) {
  const { state } = card.company.resolution;
  return state === "resolved" ? (
    <AskTheCompany card={card} />
  ) : (
    <Blocked card={card} state={state} />
  );
}
