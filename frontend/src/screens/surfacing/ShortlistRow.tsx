// One company on the list as a sheet row: rank, name, sector, signal, P, E, why, sources, deadline and the
// next step, one fact per cell on one line. The whole row opens the card; links and buttons inside it do
// their own thing.
import type { MouseEvent } from "react";
import type { ListEntry, Reason } from "../../contracts";
import { useT } from "../../i18n/messages";
import { formatDay, humanText, trunc } from "../../lib/format";
import { chipLabel, countryName, verticalText } from "../../lib/labels";
import { useMeta } from "../../lib/meta";
import { href } from "../../lib/router";
import { ChangeMarker, Chip, CountryCode } from "../../ui/Chip";
import { Deadline } from "../../ui/Deadline";
import { MiniMeter } from "../../ui/Meter";
import { RankDelta } from "../../ui/RankDelta";
import { SourceChip, sourceFromReason } from "../../ui/SourceChip";
import { Tooltip } from "../../ui/Tooltip";
import { surfacingMessages } from "./messages";
import { RankScore } from "./RankScore";

/** How a row stands out: its card is open, the J/K cursor is on it, or its Sonar blip is hovered. */
export type RowState = "open" | "cursor" | "hot" | undefined;

interface ShortlistRowProps {
  entry: ListEntry;
  /** undefined: no comparison (Blue economy preset); null: not in the Blue economy list. */
  blueRank: number | null | undefined;
  state: RowState;
  onOpen(companyId: string): void;
  onHover(companyId: string | undefined): void;
}

/** A plain left click; anything else (new tab, middle click) keeps the link's own behaviour. */
const plainClick = (e: MouseEvent) =>
  e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;

export function ShortlistRow({ entry, blueRank, state, onOpen, onHover }: ShortlistRowProps) {
  const meta = useMeta();
  const { t } = useT(surfacingMessages);
  const id = entry.company_id;
  const vertical = entry.vertical_note ?? verticalText(entry.vertical);
  const action = humanText(entry.next_action);

  const onRowClick = (e: MouseEvent<HTMLLIElement>) => {
    if (e.target instanceof Element && e.target.closest("a, button")) return;
    onOpen(id);
  };

  return (
    <li
      className="srow sheet__row sheet__row--body"
      data-row-id={id}
      data-group={entry.group}
      data-state={state}
      onClick={onRowClick}
      onPointerEnter={(e) => e.pointerType === "mouse" && onHover(id)}
      onPointerLeave={() => onHover(undefined)}
    >
      <div className="sheet__td sheet__rownum srow__rank">
        {meta.mode === "redstone" && entry.rank_parts?.total !== undefined ? (
          <RankScore parts={entry.rank_parts} total={entry.rank_parts.total}>
            {entry.rank}
          </RankScore>
        ) : (
          entry.rank
        )}
      </div>
      <RowCompany
        entry={entry}
        blueRank={blueRank}
        open={state === "open"}
        onOpen={(e) => {
          if (!plainClick(e)) return;
          e.preventDefault();
          onOpen(id);
        }}
      />
      <div className="sheet__td srow__sector">
        {vertical ? (
          <span className="sheet__text" title={humanText(vertical)}>
            {humanText(vertical)}
          </span>
        ) : (
          <span className="unknown-word">{t("sectorUnknown")}</span>
        )}
      </div>
      <div className="sheet__td srow__signal">
        <Chip tone={entry.chip === "newly_founded" ? "accent" : "grey"} dot>
          {chipLabel(entry.chip)}
        </Chip>
      </div>
      <RowScore entry={entry} kind="potential" />
      <RowScore entry={entry} kind="evidence" />
      <div className="sheet__td srow__why">
        {entry.reasons[0] ? (
          <span className="sheet__text" title={humanText(entry.reasons[0].text)}>
            {humanText(entry.reasons[0].text)}
          </span>
        ) : (
          <Chip tone="hatch">{t("noSourcedReason")}</Chip>
        )}
      </div>
      <RowSources reasons={entry.reasons} />
      <div className="sheet__td srow__deadline">
        <Deadline date={entry.deadline} today={meta.today} />
      </div>
      <div className="sheet__td srow__next">
        <span className="sheet__text" title={action}>
          {action}
        </span>
      </div>
    </li>
  );
}

interface RowCompanyProps {
  entry: ListEntry;
  blueRank: number | null | undefined;
  open: boolean;
  onOpen(e: MouseEvent<HTMLAnchorElement>): void;
}

/** Country code, name and markers; founding date and sector in the name's tooltip. */
function RowCompany({ entry, blueRank, open, onOpen }: RowCompanyProps) {
  const { t } = useT(surfacingMessages);
  const vertical = entry.vertical_note ?? verticalText(entry.vertical);
  const founded = entry.founded
    ? t("founded", { date: formatDay(entry.founded, { year: true }) })
    : t("foundedUnknown");
  const facts = [entry.name, countryName(entry.country), founded, vertical && humanText(vertical)];
  return (
    <div className="sheet__td sheet__pin srow__company">
      <span className="sheet__name">
        <CountryCode code={entry.country} />
        <a
          className="srow__name sheet__name-text"
          href={href({ name: "surfacing", companyId: entry.company_id })}
          title={facts.filter(Boolean).join(" · ")}
          aria-current={open ? "true" : undefined}
          onClick={onOpen}
        >
          {entry.name}
        </a>
        {/* Only when the API dates a change after the last digest; never inferred here. */}
        {entry.change && <ChangeMarker change={entry.change} />}
        {blueRank !== undefined && <RankDelta before={blueRank} after={entry.rank} />}
      </span>
    </div>
  );
}

/** "Potential 1.00: thesis fit 0.94 …" → "thesis fit 0.94 …": the tooltip title already says the score. */
function explanationBody(line: string | undefined): string | null {
  if (!line) return null;
  const m = /^([^:]{1,40}):\s*(.+)$/.exec(line);
  return m && /\d/.test(m[1]) ? humanText(m[2]) : humanText(line);
}

/** One score in its own cell, with the rule's explanation on hover. The API orders the explanation:
 *  potential first, then evidence, then the group. */
function RowScore({ entry, kind }: { entry: ListEntry; kind: "potential" | "evidence" }) {
  const { t } = useT(surfacingMessages);
  const value = entry.score[kind];
  const label = t(kind, { value: trunc(value) });
  const body = explanationBody(entry.score.explanation?.[kind === "potential" ? 0 : 1]);
  return (
    <div className={`sheet__td srow__score srow__score--${kind}`}>
      <Tooltip
        block
        content={
          <>
            <div className="tooltip__title mono">{label}</div>
            {body && <p>{body}</p>}
          </>
        }
      >
        <MiniMeter kind={kind} value={value} label={label} />
      </Tooltip>
    </div>
  );
}

/** The first reason's source, and the count of the other reasons with their text on hover. */
function RowSources({ reasons }: { reasons: Reason[] }) {
  const { t } = useT(surfacingMessages);
  const [first, ...more] = reasons;
  return (
    <div className="sheet__td srow__sources">
      {first && <SourceChip source={sourceFromReason(first)} index={1} short />}
      {more.length > 0 && (
        <Tooltip
          content={
            <>
              <div className="tooltip__title">{t("otherReasons")}</div>
              <ol className="srow__more-list">
                {more.map((r, i) => (
                  <li key={i}>
                    <span className="srow__more-n mono" aria-hidden="true">
                      {i + 2}
                    </span>
                    <p>{humanText(r.text)}</p>
                  </li>
                ))}
              </ol>
            </>
          }
        >
          <span
            className="srow__more mono"
            tabIndex={0}
            aria-label={t("moreReasonsSpoken", { n: more.length })}
          >
            {t("moreReasons", { n: more.length })}
          </span>
        </Tooltip>
      )}
    </div>
  );
}
