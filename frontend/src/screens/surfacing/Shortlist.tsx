// Everything on the Surfacing page that comes from the list: the header and its meta, the filters, the grouped
// capsule rows, the rail (Due next, Sonar, Sources), the foot, and the card sheet for the open row.
import { use, useMemo, useState } from "react";
import type { ListEntry } from "../../contracts";
import { load } from "../../data";
import { listRow, morph, sheetPanel } from "../../lib/motion";
import { usePreset } from "../../lib/preset";
import { navigate, navigateNow, type CardTab } from "../../lib/router";
import { useWorkspace } from "../../lib/workspace";
import { PresetSwitch } from "../../shell/PresetSwitch";
import { CardDrawer } from "./CardDrawer";
import { EmptyList } from "./EmptyList";
import { NO_FILTERS, visibleEntries, type Filters } from "./filters";
import { ListFoot } from "./ListFoot";
import { PresetBanner } from "./PresetBanner";
import type { RowState } from "./ShortlistRow";
import { ShortlistTable } from "./ShortlistTable";
import { SonarSheet } from "./SonarSheet";
import { SurfacingHeader } from "./SurfacingHeader";
import { SurfacingRail } from "./SurfacingRail";
import { Toolbar } from "./Toolbar";
import { useCloseWhenUnlisted } from "./useCloseWhenUnlisted";
import { focusRow, useListKeys } from "./useListKeys";

interface ShortlistProps {
  companyId?: string;
  tab?: CardTab;
}

/** Opens a row's card; the row grows into the sheet where the browser can. */
const open = (id: string) =>
  morph(
    "bw-card",
    listRow(id),
    () => navigateNow({ name: "surfacing", companyId: id }),
    sheetPanel,
  );

export function Shortlist({ companyId, tab }: ShortlistProps) {
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const list = use(load.list(mode, preset)).data;
  // Another preset is compared with the Blue economy list, the challenge's own ranking.
  const blueList = preset === "blue" ? null : use(load.list(mode, "blue")).data;
  const entries = list.entries;

  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [rowHoverId, setRowHoverId] = useState<string>();
  const [blipHoverId, setBlipHoverId] = useState<string | null>(null);
  const [cursorId, setCursorId] = useState<string>();
  const [sonarOpen, setSonarOpen] = useState(false);

  const visible = useMemo(() => visibleEntries(entries, filters), [entries, filters]);
  const visibleIds = useMemo(() => visible.map((e) => e.company_id), [visible]);
  const shownIds = useMemo(() => new Set(visibleIds), [visibleIds]);
  useListKeys(visibleIds, cursorId, setCursorId, companyId !== undefined || sonarOpen);
  useCloseWhenUnlisted(entries, companyId);

  const startReview = visibleIds[0]
    ? () => {
        setCursorId(visibleIds[0]);
        focusRow(visibleIds[0]);
      }
    : undefined;

  const stateOf = (id: string): RowState =>
    id === companyId
      ? "open"
      : id === blipHoverId
        ? "hot"
        : companyId === undefined && id === cursorId
          ? "cursor"
          : undefined;

  const blueRanks = blueList ? new Map(blueList.entries.map((e) => [e.company_id, e.rank])) : null;
  const dropped = blueList ? notIn(entries, blueList.entries) : [];

  return (
    <>
      <SurfacingHeader list={list} onStartReview={startReview} />
      <div className="surfacing__preset-phone">
        <PresetSwitch variant="header" />
      </div>
      {blueList && <PresetBanner />}
      {entries.length === 0 ? (
        <EmptyList whyThese={list.why_these} />
      ) : (
        <>
          <Toolbar
            entries={entries}
            filters={filters}
            onChange={setFilters}
            onOpenSonar={() => setSonarOpen(true)}
          />
          <div className="surfacing__layout">
            <div className="surfacing__main">
              <ShortlistTable
                entries={entries}
                visible={visible}
                filters={filters}
                onClearFilters={() => setFilters(NO_FILTERS)}
                blueRanks={blueRanks}
                stateOf={stateOf}
                onOpen={open}
                onHover={setRowHoverId}
              />
              <ListFoot list={list} dropped={dropped} />
            </div>
            <SurfacingRail
              list={list}
              shownIds={shownIds}
              hotId={rowHoverId ?? blipHoverId ?? companyId ?? cursorId}
              onOpen={open}
              onBlipHover={setBlipHoverId}
            />
          </div>
          <SonarSheet
            open={sonarOpen}
            entries={entries}
            shownIds={shownIds}
            onClose={() => setSonarOpen(false)}
            onChoose={(id) => {
              setSonarOpen(false);
              navigate({ name: "surfacing", companyId: id });
            }}
          />
        </>
      )}
      <CardDrawer entries={entries} companyId={companyId} tab={tab} />
    </>
  );
}

/** Rows of `other` that `entries` does not hold. */
function notIn(entries: ListEntry[], other: ListEntry[]): ListEntry[] {
  const listed = new Set(entries.map((e) => e.company_id));
  return other.filter((e) => !listed.has(e.company_id));
}
