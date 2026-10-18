// The open bridge: the company and its evidence on one side, the counterparty and its evidence on the
// other, joined by the dated reason to act now and one action.
import { TriangleAlert } from "lucide-react";
import type { Bridge } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { bridgeType } from "../../lib/labels";
import { shellMessages } from "../../shell/messages";
import { Chip, ConfidenceChip } from "../../ui/Chip";
import { Panel } from "../../ui/Panel";
import { Connector } from "./Connector";
import { dateMeaning } from "./dateMeaning";
import { DraftAction } from "./DraftAction";
import { EvidenceList } from "./EvidenceList";
import { hideName, type Alias } from "./hideNames";
import { bridgesMessages } from "./messages";
import { PartyHead } from "./PartyHead";
import { bridgeSource } from "./sources";

interface BridgeHeroProps {
  bridge: Bridge;
  today: string;
  alias: Alias | null;
  /** The bridges came from the recorded fallback, not the live API. */
  recorded: boolean;
}

export function BridgeHero({ bridge, today, alias, recorded }: BridgeHeroProps) {
  const { t } = useT(bridgesMessages);
  const shell = useT(shellMessages);
  const type = bridgeType(bridge.type);
  const words = (text: string) => humanText(hideName(text, alias));
  const companyName = alias?.name ?? humanText(bridge.company.name);
  const companySources = bridge.evidence_company.map((e) =>
    bridgeSource(e, bridge.company.country, alias !== null),
  );
  // A page that backs both sides (a project page lists every participant) would name the company too.
  const companyUrls = new Set(bridge.evidence_company.map((e) => e.url));
  const counterpartySources = bridge.evidence_counterparty.map((e) =>
    bridgeSource(e, null, alias !== null && !!e.url && companyUrls.has(e.url)),
  );

  return (
    <Panel className="bridge-hero" labelledBy="bridge-hero-reason">
      <header className="bridge-hero__head">
        <p className="overline">
          {bridge.generator === "seed" && (
            <span className="mono">{shell.t("bridgeId", { id: bridge.id })} · </span>
          )}
          {type.label}
        </p>
        <span className="bridge-hero__chips">
          {recorded && <Chip title={shell.t("demoTitle")}>{shell.t("demoData")}</Chip>}
          <ConfidenceChip confidence={bridge.confidence} />
        </span>
        <p className="bridge-hero__explainer">{type.explainer}</p>
      </header>

      <h2 className="bridge-hero__reason" id="bridge-hero-reason">
        {words(bridge.reason)}
      </h2>

      <div className="bridge-hero__grid">
        <PartyHead side="company" party={bridge.company} alias={alias?.name} />
        <EvidenceList
          side="company"
          items={bridge.evidence_company}
          sources={companySources}
          firstIndex={1}
          today={today}
          partyName={companyName}
          words={words}
        />
        <Connector
          label={type.label}
          date={bridge.deadline}
          meaning={dateMeaning(bridge)}
          today={today}
        />
        <PartyHead side="counterparty" party={bridge.counterparty} />
        <EvidenceList
          side="counterparty"
          items={bridge.evidence_counterparty}
          sources={counterpartySources}
          firstIndex={companySources.length + 1}
          today={today}
          partyName={humanText(bridge.counterparty.name)}
          words={words}
        />
      </div>

      {bridge.caveat && (
        <p className="bridge-hero__caveat callout callout--amber">
          <TriangleAlert size={16} strokeWidth={1.75} aria-hidden="true" />
          <span>
            <strong>{t("caveat")}:</strong> {words(bridge.caveat)}
          </span>
        </p>
      )}

      <div className="bridge-hero__action">
        <div className="bridge-hero__next">
          <p className="overline">{t("nextAction")}</p>
          <p className="bridge-hero__action-text">{words(bridge.action)}</p>
          <p className="bridge-hero__note">{t("approvalNote")}</p>
        </div>
        <DraftAction bridge={bridge} />
      </div>
    </Panel>
  );
}
