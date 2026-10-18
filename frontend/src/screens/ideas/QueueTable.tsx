// The queue on a desktop, laid out as a sheet like Companies and Now Surfacing: one line per idea, one fact
// per column (idea, source, tier, potential and evidence, why it's here, next step, flags). The whole row
// opens its card; the title stays a real link (middle click opens a new tab).
import {
  Activity,
  Flag as FlagIcon,
  Layers,
  Lightbulb,
  ListChecks,
  Sparkles,
  Trophy,
  type LucideIcon,
} from "lucide-react";
import type { MouseEvent } from "react";
import { useT } from "../../i18n/messages";
import { vars } from "../../lib/motion";
import { href } from "../../lib/router";
import { shellMessages } from "../../shell/messages";
import { ROW_NUMBER_WIDTH, sheetTracks, type ColumnWidth } from "../../ui/DataTable";
import "../../ui/DataTable.css";
import { Tooltip } from "../../ui/Tooltip";
import { ideasMessages } from "./messages";
import { onCardLink, openItem, type RowContext } from "./queueRow";
import { BandPills } from "./read/Bands";
import { IdeaTierChip, OriginChip } from "./read/chips";
import { readableDates } from "./read/hooks";
import { FLAG_ICON, STEP_ICON } from "./read/icons";
import { readMessages } from "./read/messages";
import { SampleChip } from "./SampleData";
import type { Flag, QueueItem } from "./types";

type HeaderKey =
  "col_idea" | "col_source" | "col_tier" | "col_bands" | "col_why" | "col_next" | "col_flags";

const COLUMNS: { key: HeaderKey; icon: LucideIcon; width: ColumnWidth }[] = [
  { key: "col_idea", icon: Lightbulb, width: 220 },
  { key: "col_source", icon: Trophy, width: 160 },
  { key: "col_tier", icon: Layers, width: 216 },
  { key: "col_bands", icon: Activity, width: 274 },
  { key: "col_why", icon: Sparkles, width: { min: 178, fr: 1.5 } },
  { key: "col_next", icon: ListChecks, width: { min: 170, fr: 1 } },
  { key: "col_flags", icon: FlagIcon, width: 96 },
];

const TRACKS = sheetTracks([ROW_NUMBER_WIDTH, ...COLUMNS.map((c) => c.width)]);

interface QueueTableProps {
  items: QueueItem[];
  topN: number;
  context: RowContext;
}

export function QueueTable({ items, topN, context }: QueueTableProps) {
  const { t } = useT(ideasMessages);
  const shell = useT(shellMessages);
  return (
    <div
      className="ih-sheet sheet"
      style={vars({
        "--cols": TRACKS.cols,
        "--sheet-min": TRACKS.minWidth,
        "--pin-left": `${ROW_NUMBER_WIDTH}px`,
      })}
    >
      <div className="sheet__grid" role="table" aria-label={shell.t("page_ideas")}>
        <div role="rowgroup" className="sheet__head">
          <div role="row" className="sheet__row sheet__row--head">
            <div role="columnheader" className="sheet__th sheet__rownum">
              #
            </div>
            {COLUMNS.map(({ key, icon: Icon }, i) => (
              <div
                key={key}
                role="columnheader"
                className={`sheet__th${i === 0 ? " sheet__pin" : ""}`}
              >
                <Icon size={15} strokeWidth={1.7} aria-hidden="true" />
                <span className="sheet__th-label">{t(key)}</span>
              </div>
            ))}
          </div>
        </div>
        <div role="rowgroup" className="sheet__body">
          {items.map((item) => (
            <Row key={item.id} item={item} topN={topN} context={context} />
          ))}
        </div>
      </div>
    </div>
  );
}

interface RowProps {
  item: QueueItem;
  topN: number;
  context: RowContext;
}

function Row({ item, topN, context }: RowProps) {
  const { t } = useT(ideasMessages);
  const read = item.assessment;
  const duplicateOf = context.duplicateOf(item);
  const selected = item.id === context.selectedId;
  const why = item.why_here[1] ? readableDates(item.why_here[1], context.today) : null;
  const onClick = (e: MouseEvent<HTMLDivElement>) => {
    if (e.target instanceof HTMLElement && e.target.closest("a, button")) return;
    openItem(item);
  };
  return (
    <div
      ref={context.rowRef(item.id)}
      role="row"
      data-row-id={item.id}
      className={`sheet__row sheet__row--body ih-srow${selected ? " is-selected" : ""}${item.in_top ? " ih-srow--top" : ""}`}
      aria-current={selected || undefined}
      onClick={onClick}
    >
      <div
        role="cell"
        className="sheet__td sheet__rownum"
        title={item.in_top ? t("topN", { n: topN }) : undefined}
      >
        {item.rank}
        {item.in_top && <span className="sr-only">{t("topN", { n: topN })}</span>}
      </div>
      <div role="cell" className="sheet__td sheet__pin">
        <a
          className="sheet__name-text ih-srow__title"
          href={href({ name: "ideas", itemId: item.id })}
          title={read.title}
          onClick={(e) => onCardLink(e, item)}
        >
          {read.title}
        </a>
      </div>
      <div role="cell" className="sheet__td">
        {context.sample && <SampleChip />}
        <OriginChip kind={item.origin.kind} />
      </div>
      <div role="cell" className="sheet__td">
        <IdeaTierChip tier={read.tier} label={read.tier_label} />
      </div>
      <div role="cell" className="sheet__td">
        <BandPills read={read} />
      </div>
      <div role="cell" className="sheet__td">
        {duplicateOf ? (
          <a
            className="sheet__text ih-srow__dup"
            href={href({ name: "ideas", itemId: duplicateOf.id })}
            onClick={(e) => onCardLink(e, duplicateOf)}
          >
            {t("readsLike", { rank: duplicateOf.rank, title: duplicateOf.assessment.title })}
          </a>
        ) : why ? (
          <span className="sheet__text ih-srow__why" title={why}>
            {why}
          </span>
        ) : (
          <span className="sheet__muted">{"·"}</span>
        )}
      </div>
      <div role="cell" className="sheet__td">
        <NextStep item={item} />
      </div>
      <div role="cell" className="sheet__td">
        <RowFlags
          flags={read.flags}
          claudeNote={read.reader === "rules_and_model" ? read.reader_note : null}
        />
      </div>
    </div>
  );
}

function NextStep({ item }: { item: QueueItem }) {
  const { t } = useT(ideasMessages);
  const step = item.assessment.next_steps[0];
  if (!step) return <span className="sheet__muted">{t("noNextStep")}</span>;
  const Icon = STEP_ICON[step.kind];
  return (
    <>
      <Icon className="ih-srow__step-icon" size={15} strokeWidth={1.5} aria-hidden="true" />
      <span className="sheet__text ih-srow__next" title={step.title}>
        {step.title}
      </span>
    </>
  );
}

/** The row's flags as icons with their words on hover, and a sparkle when Claude listed quoted claims. */
function RowFlags({ flags, claudeNote }: { flags: Flag[]; claudeNote: string | null }) {
  const { t } = useT(ideasMessages);
  const read = useT(readMessages);
  if (flags.length === 0 && !claudeNote) return null;
  return (
    <ul className="ih-row__flags" aria-label={t("col_flags")}>
      {claudeNote && (
        <li>
          <Tooltip content={`${read.t("claudeRead")}: ${claudeNote}`}>
            <span
              className="ih-flag ih-flag--claude"
              tabIndex={0}
              aria-label={read.t("claudeRead")}
            >
              <Sparkles size={14} strokeWidth={1.5} aria-hidden="true" />
            </span>
          </Tooltip>
        </li>
      )}
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
