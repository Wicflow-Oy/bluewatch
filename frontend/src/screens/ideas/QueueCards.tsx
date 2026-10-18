// The queue below a desktop: each idea is one capsule card (two columns on a tablet) that opens its idea card.
import { useT } from "../../i18n/messages";
import { href } from "../../lib/router";
import { ideasMessages } from "./messages";
import { vars } from "../../lib/motion";
import { onCardLink, type RowContext } from "./queueRow";
import { BandPills } from "./read/Bands";
import { ClaudeChip, IdeaTierChip, OriginChip } from "./read/chips";
import { readableDates } from "./read/hooks";
import { FLAG_ICON, STEP_ICON } from "./read/icons";
import { SampleChip } from "./SampleData";
import type { QueueItem } from "./types";

export function QueueCards({ items, context }: { items: QueueItem[]; context: RowContext }) {
  return (
    <ul className="ih-cards">
      {items.map((item, index) => (
        <li key={item.id} ref={context.rowRef(item.id)}>
          <Card item={item} index={index} context={context} />
        </li>
      ))}
    </ul>
  );
}

function Card({ item, index, context }: { item: QueueItem; index: number; context: RowContext }) {
  const { t } = useT(ideasMessages);
  const read = item.assessment;
  const duplicateOf = context.duplicateOf(item);
  const step = read.next_steps[0];
  const StepIcon = step ? STEP_ICON[step.kind] : null;
  return (
    <a
      className={`ih-card capsule capsule--interactive${item.id === context.selectedId ? " is-selected" : ""}`}
      href={href({ name: "ideas", itemId: item.id })}
      data-row-id={item.id}
      style={vars({ "--i": index })}
      onClick={(e) => onCardLink(e, item)}
    >
      <span className="ih-card__head">
        <span className={`ih-rank mono${item.in_top ? " ih-rank--top" : ""}`}>{item.rank}</span>
        <span className="ih-card__title">{read.title}</span>
      </span>
      <span className="ih-card__chips">
        <IdeaTierChip tier={read.tier} label={read.tier_label} />
        {context.sample && <SampleChip />}
        <OriginChip kind={item.origin.kind} />
        {read.reader === "rules_and_model" && <ClaudeChip note={read.reader_note} plain />}
      </span>
      <BandPills read={read} labelled />
      {item.why_here[1] && (
        <span className="ih-card__why">{readableDates(item.why_here[1], context.today)}</span>
      )}
      {step && StepIcon && (
        <span className="ih-card__next">
          <StepIcon size={15} strokeWidth={1.5} aria-hidden="true" />
          <span>{step.title}</span>
        </span>
      )}
      {duplicateOf && (
        <span className="ih-card__dup">
          {t("readsLike", { rank: duplicateOf.rank, title: duplicateOf.assessment.title })}
        </span>
      )}
      {read.flags.length > 0 && (
        <span className="ih-card__flags">
          {read.flags.map((flag) => {
            const FlagIcon = FLAG_ICON[flag.kind];
            return (
              <span key={flag.kind} className="ih-flag" title={flag.text}>
                <FlagIcon size={14} strokeWidth={1.5} aria-hidden="true" />
                <span className="sr-only">{flag.text}</span>
              </span>
            );
          })}
        </span>
      )}
    </a>
  );
}
