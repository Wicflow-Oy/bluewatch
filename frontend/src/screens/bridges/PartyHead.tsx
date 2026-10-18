// One side of a bridge: what kind of party it is, its name, and where to check it.
import { ArrowRight } from "lucide-react";
import type { BridgeParty } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText, registryLabel } from "../../lib/format";
import { href } from "../../lib/router";
import { bridgesMessages } from "./messages";

export type Side = "company" | "counterparty";

const PARTY_KINDS = [
  "company",
  "research_group",
  "programme",
  "funder",
  "research_infrastructure",
  "public_buyer",
  "corporate",
  "corporate_and_public",
  "research_org",
  "port",
  "shipowner",
] as const;
type PartyKind = (typeof PARTY_KINDS)[number];

function isPartyKind(kind: string): kind is PartyKind {
  return (PARTY_KINDS as readonly string[]).includes(kind);
}

/** "FI:3101791-3" when the party has no separate registry_id. */
function registerOf(party: BridgeParty): string | null {
  const [country, id] = party.company_id?.split(":") ?? [];
  const registryId = party.registry_id ?? id;
  const registryCountry = party.country ?? country;
  return registryId && registryCountry ? registryLabel(registryCountry, registryId) : null;
}

interface PartyHeadProps {
  side: Side;
  party: BridgeParty;
  /** Stands in for the name while names are hidden; the register ID and card link are hidden too. */
  alias?: string;
}

export function PartyHead({ side, party, alias }: PartyHeadProps) {
  const { t } = useT(bridgesMessages);
  const kind = party.kind ?? side;
  const sideWord = side === "company" ? t("kind_company") : t("counterparty");
  const overline = isPartyKind(kind) ? t(`kind_${kind}`) : sideWord;
  const shown = alias === undefined;
  const register = shown ? registerOf(party) : null;
  const cardId = shown ? party.company_id : null;
  return (
    <div className={`bridge-party bridge-party--${side}`}>
      <p className="overline">{overline}</p>
      <p className="bridge-party__name">{alias ?? humanText(party.name)}</p>
      {(register || cardId) && (
        <p className="bridge-party__meta">
          {register && <span className="mono">{register}</span>}
          {cardId && (
            <a href={href({ name: "card", companyId: cardId })}>
              {t("ventureCard")}
              <ArrowRight size={12} strokeWidth={1.75} aria-hidden="true" />
            </a>
          )}
        </p>
      )}
    </div>
  );
}
