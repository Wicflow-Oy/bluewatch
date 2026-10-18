// The list itself, laid out as a sheet: the column head once, then each shown group as a header row with its
// rule, followed by one line per company. One fact per column, the way a spreadsheet lays out leads.
import {
  Activity,
  Building2,
  Clock,
  Link2,
  ListChecks,
  ShieldCheck,
  Sparkles,
  Tag,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import type { ListEntry } from "../../contracts";
import { useT } from "../../i18n/messages";
import { vars } from "../../lib/motion";
import { useMeta } from "../../lib/meta";
import { GroupDot } from "../../ui/Chip";
import { ROW_NUMBER_WIDTH, sheetTracks, type ColumnWidth } from "../../ui/DataTable";
import { EmptyState } from "../../ui/States";
import type { Filters } from "./filters";
import { SURFACING_GROUPS, type SurfacingGroup } from "./groups";
import { surfacingMessages, type SurfacingKey } from "./messages";
import { ShortlistRow, type RowState } from "./ShortlistRow";

/** The name column stays in view when the sheet scrolls sideways, right after the rank. */
export const NAME_WIDTH = 200;

const COLUMNS: { key: SurfacingKey; icon: LucideIcon; width: ColumnWidth }[] = [
  { key: "colCompany", icon: Building2, width: NAME_WIDTH },
  { key: "colSector", icon: Tag, width: { min: 104, fr: 0.8 } },
  { key: "colSignal", icon: Activity, width: 160 },
  { key: "colPotential", icon: TrendingUp, width: 108 },
  { key: "colEvidence", icon: ShieldCheck, width: 108 },
  { key: "colWhy", icon: Sparkles, width: { min: 200, fr: 1.6 } },
  { key: "colSources", icon: Link2, width: 120 },
  { key: "colDeadline", icon: Clock, width: 160 },
  { key: "colNext", icon: ListChecks, width: { min: 170, fr: 1.4 } },
];

const TRACKS = sheetTracks([ROW_NUMBER_WIDTH, ...COLUMNS.map((c) => c.width)]);

interface ShortlistTableProps {
  entries: ListEntry[];
  /** The rows the filters let through, in display order. */
  visible: ListEntry[];
  filters: Filters;
  onClearFilters(): void;
  /** Rank of each company in the Blue economy list, when another preset is active. */
  blueRanks: Map<string, number> | null;
  stateOf(companyId: string): RowState;
  onOpen(companyId: string): void;
  onHover(companyId: string | undefined): void;
}

export function ShortlistTable({
  entries,
  visible,
  filters,
  onClearFilters,
  blueRanks,
  stateOf,
  onOpen,
  onHover,
}: ShortlistTableProps) {
  const { t } = useT(surfacingMessages);
  const meta = useMeta();
  // A group the list itself left empty says so; a group the signal chips emptied is just not shown.
  const groups = SURFACING_GROUPS.filter((g) => filters.group === "all" || filters.group === g)
    .map((group) => ({
      group,
      listed: entries.some((e) => e.group === group),
      rows: visible.filter((e) => e.group === group),
    }))
    .filter((g) => g.rows.length > 0 || !g.listed);

  // Nothing left to show at all: the filters emptied the list.
  if (groups.length === 0) {
    return (
      <div className="shortlist">
        <EmptyState
          compact
          title={t("noneMatch")}
          action={
            <button type="button" className="btn btn--sm" onClick={onClearFilters}>
              {t("clearFilters")}
            </button>
          }
        />
      </div>
    );
  }

  return (
    <div
      className="shortlist sheet"
      style={vars({
        "--cols": TRACKS.cols,
        "--sheet-min": TRACKS.minWidth,
        "--pin-left": `${ROW_NUMBER_WIDTH}px`,
      })}
    >
      <div className="sheet__grid">
        <ColumnHead />
        {groups.map(({ group, rows }) => (
          <section key={group} className="shortlist__group" aria-label={meta.group(group)}>
            <GroupHeader group={group} count={rows.length} />
            {rows.length === 0 ? (
              <p className="shortlist__empty">
                <strong>{t("noneThisWeek")}</strong> {t("neverPadded")}
              </p>
            ) : (
              <ol className="shortlist__rows">
                {rows.map((entry) => (
                  <ShortlistRow
                    key={entry.company_id}
                    entry={entry}
                    blueRank={blueRanks ? (blueRanks.get(entry.company_id) ?? null) : undefined}
                    state={stateOf(entry.company_id)}
                    onOpen={onOpen}
                    onHover={onHover}
                  />
                ))}
              </ol>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

function GroupHeader({ group, count }: { group: SurfacingGroup; count: number }) {
  const { t } = useT(surfacingMessages);
  const meta = useMeta();
  return (
    <header className="shortlist__group-head">
      <span className="shortlist__group-label">
        <GroupDot group={group} />
        <h3 className="shortlist__group-name">{meta.group(group)}</h3>
        <span className="shortlist__group-count mono">{count}</span>
        <span className="shortlist__group-rule">{t(`rule_${group}`)}</span>
      </span>
    </header>
  );
}

function ColumnHead() {
  const { t } = useT(surfacingMessages);
  return (
    <div className="sheet__head shortlist__colhead" aria-hidden="true">
      <div className="sheet__row sheet__row--head">
        <span className="sheet__th sheet__rownum">#</span>
        {COLUMNS.map(({ key, icon: Icon }, i) => (
          <span key={key} className={`sheet__th${i === 0 ? " sheet__pin" : ""}`}>
            <Icon size={14} strokeWidth={1.6} aria-hidden="true" />
            <span className="sheet__th-label">{t(key)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
