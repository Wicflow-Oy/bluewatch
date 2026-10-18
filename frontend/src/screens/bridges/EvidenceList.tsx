// The sourced claims for one side of a bridge. Claims are evidence from the API, shown as written.
import type { BridgeEvidence } from "../../contracts";
import { useT } from "../../i18n/messages";
import { formatEventDate } from "../../lib/format";
import { Deadline } from "../../ui/Deadline";
import { SourceChip, type SourceRef } from "../../ui/SourceChip";
import { bridgesMessages } from "./messages";
import type { Side } from "./PartyHead";

interface EvidenceListProps {
  side: Side;
  items: BridgeEvidence[];
  sources: SourceRef[];
  /** Source numbers run on across both sides of the card. */
  firstIndex: number;
  today: string;
  /** The party's name as shown, for the list's accessible name. */
  partyName: string;
  words(text: string): string;
}

export function EvidenceList({
  side,
  items,
  sources,
  firstIndex,
  today,
  partyName,
  words,
}: EvidenceListProps) {
  const { t } = useT(bridgesMessages);
  return (
    <ul
      className={`bridge-evidence bridge-evidence--${side}`}
      aria-label={t("evidenceFor", { name: partyName })}
    >
      {items.map((item, i) => (
        <li key={`${item.url ?? ""}${item.claim}`} className="bridge-evidence__item">
          <p className="bridge-evidence__claim">{words(item.claim)}</p>
          <p className="bridge-evidence__source">
            <SourceChip source={sources[i]} index={firstIndex + i} />
            {item.date && <span className="mono muted">{formatEventDate(item.date, today)}</span>}
          </p>
          {item.deadline && (
            <span className="bridge-evidence__deadline">
              <Deadline date={item.deadline} today={today} />
            </span>
          )}
        </li>
      ))}
      {items.length === 0 && <li className="bridge-evidence__none">{t("noEvidence")}</li>}
    </ul>
  );
}
