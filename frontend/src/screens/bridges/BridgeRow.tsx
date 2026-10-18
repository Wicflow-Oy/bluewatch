import type { Bridge } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { bridgeType } from "../../lib/labels";
import { href } from "../../lib/router";
import { ConfidenceChip } from "../../ui/Chip";
import { Deadline } from "../../ui/Deadline";
import { dateMeaning } from "./dateMeaning";
import { bridgesMessages } from "./messages";

interface BridgeRowProps {
  bridge: Bridge;
  today: string;
  /** The name to show for the company: a description while names are hidden. */
  companyName?: string;
}

/** One bridge as a compact link row: type, the two parties, the date and how sure we are. */
export function BridgeRow({ bridge, today, companyName = bridge.company.name }: BridgeRowProps) {
  const { t } = useT(bridgesMessages);
  const company = humanText(companyName);
  const counterparty = humanText(bridge.counterparty.name);
  const meaning = dateMeaning(bridge);
  return (
    <a
      className="bridge-row capsule capsule--interactive"
      href={href({ name: "bridges", bridgeId: bridge.id })}
      data-row-id={bridge.id}
    >
      <span className="bridge-row__main">
        <span className="bridge-row__type">
          <span className="bridge-row__dot" aria-hidden="true" />
          {bridgeType(bridge.type).label}
        </span>
        <span className="bridge-row__parties" title={`${company} → ${counterparty}`}>
          <span aria-hidden="true">
            {company}
            <span className="bridge-row__arrow">{" → "}</span>
            {counterparty}
          </span>
          <span className="sr-only">{t("parties", { company, counterparty })}</span>
        </span>
      </span>
      <span className="bridge-row__deadline">
        {bridge.deadline && meaning !== "deadline" && (
          <span className="bridge-row__when">{t(`when_${meaning}`)}</span>
        )}
        <Deadline date={bridge.deadline} today={today} />
      </span>
      <span className="bridge-row__confidence">
        <ConfidenceChip confidence={bridge.confidence} />
      </span>
    </a>
  );
}
