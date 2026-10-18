// The right rail: what is due next, the Sonar (not on phones: there it is a sheet), and every source's state.
import { use } from "react";
import type { ShortList } from "../../contracts";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { formatStamp } from "../../lib/format";
import { useIsPhone } from "../../lib/media";
import { Panel } from "../../ui/Panel";
import { SonarPlot } from "../../ui/SonarPlot";
import { sonarMessages } from "../../ui/SonarPlot.messages";
import { SourceRows } from "../../ui/SourceStatusPill";
import { surfacingMessages } from "./messages";
import { RailDeadlines } from "./RailDeadlines";
import { sonarPoints } from "./sonarPoints";

interface SurfacingRailProps {
  list: ShortList;
  /** The rows the toolbar's filters let through; the other blips are dimmed. */
  shownIds: ReadonlySet<string>;
  /** The hot blip: a hovered row, the J/K cursor or the open card. */
  hotId?: string;
  onOpen(companyId: string): void;
  onBlipHover(companyId: string | null): void;
}

export function SurfacingRail({ list, shownIds, hotId, onOpen, onBlipHover }: SurfacingRailProps) {
  const { t } = useT(surfacingMessages);
  const sonar = useT(sonarMessages);
  const phone = useIsPhone();
  const { attribution } = use(load.meta()).data;
  const sources = list.sources ?? [];
  return (
    <aside className="surfacing__rail" aria-label={t("rail")}>
      <RailDeadlines entries={list.entries} />
      {!phone && (
        <Panel
          className="surfacing__sonar"
          title={sonar.t("sonar")}
          meta={sonar.t("sonarAux", { n: list.entries.length })}
        >
          <SonarPlot
            points={sonarPoints(list.entries, shownIds)}
            selectedId={hotId}
            onSelect={onOpen}
            onHover={onBlipHover}
          />
        </Panel>
      )}
      {sources.length > 0 && (
        <Panel
          className="surfacing__sources"
          title={t("sources")}
          meta={<span className="mono">{formatStamp(list.generated_at)}</span>}
        >
          <SourceRows sources={sources} attribution={attribution} />
        </Panel>
      )}
    </aside>
  );
}
