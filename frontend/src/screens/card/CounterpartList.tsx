// Buyers, partners and bridges as capsule rows; a bridge row opens its bridge.
import type { Bridge, Opportunity } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { bridgeType, stepKindLabel } from "../../lib/labels";
import { href } from "../../lib/router";
import { ConfidenceChip } from "../../ui/Chip";
import { Deadline } from "../../ui/Deadline";
import { KindIcon } from "../../ui/KindIcon";
import { uiMessages } from "../../ui/messages";

function DeadlineOrNone({ date, today }: { date: string | null | undefined; today: string }) {
  const { t } = useT(uiMessages);
  return date ? (
    <Deadline date={date} today={today} />
  ) : (
    <span className="row-none">{t("noDeadline")}</span>
  );
}

function BridgeRow({ bridge, today }: { bridge: Bridge; today: string }) {
  return (
    <li>
      <a
        className="card-row capsule-row card-row--link"
        href={href({ name: "bridges", bridgeId: bridge.id })}
      >
        <span className="card-row__main">
          <span className="overline">{bridgeType(bridge.type).label}</span>
          <span className="card-row__title">{bridge.counterparty.name}</span>
        </span>
        <DeadlineOrNone date={bridge.deadline} today={today} />
        <ConfidenceChip confidence={bridge.confidence} />
      </a>
    </li>
  );
}

function CounterpartRow({ opportunity, today }: { opportunity: Opportunity; today: string }) {
  return (
    <li className="card-row capsule-row">
      <span className="card-row__main">
        <span className="overline card-row__kind">
          <KindIcon kind={opportunity.kind} />
          {stepKindLabel(opportunity.kind)}
        </span>
        <span className="card-row__title">{opportunity.title}</span>
        <span className="card-row__sub">{humanText(opportunity.action)}</span>
      </span>
      <DeadlineOrNone date={opportunity.deadline} today={today} />
    </li>
  );
}

interface CounterpartListProps {
  bridges: Bridge[];
  counterparts: Opportunity[];
  today: string;
}

export function CounterpartList({ bridges, counterparts, today }: CounterpartListProps) {
  return (
    <ul className="card-rows">
      {bridges.map((b) => (
        <BridgeRow key={b.id} bridge={b} today={today} />
      ))}
      {counterparts.map((o) => (
        <CounterpartRow key={o.id} opportunity={o} today={today} />
      ))}
    </ul>
  );
}
