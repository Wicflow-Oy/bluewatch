// The queue on a desktop: one capsule row per idea under a sticky frosted head. The whole row opens its
// card; the title stays a real link (middle click opens a new tab) and "+n" unfolds the reasons in place.
import { ArrowRight } from "lucide-react";
import { useState, type MouseEvent, type ReactNode } from "react";
import { useT } from "../../i18n/messages";
import { vars } from "../../lib/motion";
import { href } from "../../lib/router";
import { shellMessages } from "../../shell/messages";
import { Tooltip } from "../../ui/Tooltip";
import { ideasMessages } from "./messages";
import { onCardLink, openItem, type RowContext } from "./queueRow";
import { BandPills } from "./read/Bands";
import { ClaudeChip, IdeaTierChip, OriginChip } from "./read/chips";
import { readableDates } from "./read/hooks";
import { FLAG_ICON, STEP_ICON } from "./read/icons";
import { SampleChip } from "./SampleData";
import type { Flag, QueueItem } from "./types";

interface QueueTableProps {
  items: QueueItem[];
  topN: number;
  context: RowContext;
}

export function QueueTable({ items, topN, context }: QueueTableProps) {
  const { t } = useT(ideasMessages);
  const shell = useT(shellMessages);
  return (
    <div className="ih-table" role="table" aria-label={shell.t("page_ideas")}>
      <div role="rowgroup" className="ih-table__head">
        <div role="row" className="ih-table__row">
          <div role="columnheader">#</div>
          <div role="columnheader">{t("col_idea")}</div>
          <div role="columnheader">{t("col_read")}</div>
          <div role="columnheader">{t("col_bands")}</div>
          <div role="columnheader">{t("col_next")}</div>
          <div role="columnheader">{t("col_flags")}</div>
        </div>
      </div>
      <div role="rowgroup" className="ih-table__body">
        {items.map((item, index) => (
          <Row key={item.id} item={item} index={index} topN={topN} context={context} />
        ))}
      </div>
    </div>
  );
}

interface RowProps {
  item: QueueItem;
  index: number;
  topN: number;
  context: RowContext;
}

function Row({ item, index, topN, context }: RowProps) {
  const { t } = useT(ideasMessages);
  const read = item.assessment;
  const duplicateOf = context.duplicateOf(item);
  const selected = item.id === context.selectedId;
  const onClick = (e: MouseEvent<HTMLDivElement>) => {
    if (e.target instanceof HTMLElement && e.target.closest("a, button")) return;
    openItem(item);
  };
  return (
    <div
      ref={context.rowRef(item.id)}
      role="row"
      data-row-id={item.id}
      className={`ih-table__row ih-row capsule capsule--interactive${selected ? " is-selected" : ""}`}
      aria-current={selected || undefined}
      style={vars({ "--i": index })}
      onClick={onClick}
    >
      <div role="cell" className="ih-row__rank">
        <span
          className={`ih-rank mono${item.in_top ? " ih-rank--top" : ""}`}
          title={item.in_top ? t("topN", { n: topN }) : undefined}
        >
          {item.rank}
        </span>
        {/* The ink tile marks the top slots; the words are for screen readers and the tooltip. */}
        {item.in_top && <span className="sr-only">{t("topN", { n: topN })}</span>}
      </div>
      <div role="cell" className="ih-row__idea">
        <a
          className="ih-row__title"
          href={href({ name: "ideas", itemId: item.id })}
          onClick={(e) => onCardLink(e, item)}
        >
          {read.title}
        </a>
        <WhyHere lines={item.why_here} today={context.today}>
          {context.sample && <SampleChip />}
          <OriginChip kind={item.origin.kind} />
        </WhyHere>
        {duplicateOf && (
          <a
            className="ih-row__dup"
            href={href({ name: "ideas", itemId: duplicateOf.id })}
            onClick={(e) => onCardLink(e, duplicateOf)}
          >
            {t("readsLike", { rank: duplicateOf.rank, title: duplicateOf.assessment.title })}
          </a>
        )}
      </div>
      <div role="cell" className="ih-row__chips">
        <IdeaTierChip tier={read.tier} label={read.tier_label} />
        {read.reader === "rules_and_model" && <ClaudeChip note={read.reader_note} />}
      </div>
      <div role="cell">
        <BandPills read={read} />
      </div>
      <div role="cell">
        <NextStep item={item} />
      </div>
      <div role="cell" className="ih-row__end">
        <RowFlags flags={read.flags} />
        <span className="ih-row__open" aria-hidden="true">
          <ArrowRight size={14} strokeWidth={1.75} />
        </span>
      </div>
    </div>
  );
}

/**
 * The first reason after the band line, then the row's chips; "+n" beside them shows the rest of the
 * reasons in place without opening the card.
 */
function WhyHere({
  lines,
  today,
  children,
}: {
  lines: string[];
  today: string;
  children: ReactNode;
}) {
  const { t } = useT(ideasMessages);
  const [open, setOpen] = useState(false);
  const first = lines[1] ? readableDates(lines[1], today) : null;
  const rest = lines.slice(2);
  return (
    <>
      {first && (
        <p className="ih-why__line" title={first}>
          {first}
        </p>
      )}
      {open && (
        <ul className="ih-why__rest">
          {rest.map((line) => (
            <li key={line}>{readableDates(line, today)}</li>
          ))}
        </ul>
      )}
      <div className="ih-row__chips">
        {children}
        {first && rest.length > 0 && (
          <button
            type="button"
            className="ih-more mono"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? t("showLess") : `+${rest.length}`}
          </button>
        )}
      </div>
    </>
  );
}

function NextStep({ item }: { item: QueueItem }) {
  const { t } = useT(ideasMessages);
  const step = item.assessment.next_steps[0];
  if (!step) return <span className="ih-caption">{t("noNextStep")}</span>;
  const Icon = STEP_ICON[step.kind];
  return (
    <p className="ih-next" title={step.title}>
      <Icon size={15} strokeWidth={1.5} aria-hidden="true" />
      <span>{step.title}</span>
    </p>
  );
}

function RowFlags({ flags }: { flags: Flag[] }) {
  const { t } = useT(ideasMessages);
  if (flags.length === 0) return <span />;
  return (
    <ul className="ih-row__flags" aria-label={t("col_flags")}>
      {flags.map((flag) => {
        const Icon = FLAG_ICON[flag.kind];
        return (
          <li key={flag.kind}>
            <Tooltip content={flag.text}>
              <span className="ih-flag" tabIndex={0} aria-label={flag.text}>
                <Icon size={14} strokeWidth={1.5} aria-hidden="true" />
              </span>
            </Tooltip>
          </li>
        );
      })}
    </ul>
  );
}
