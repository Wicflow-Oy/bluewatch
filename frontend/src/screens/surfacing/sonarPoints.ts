import type { ListEntry } from "../../contracts";
import type { SonarPoint } from "../../ui/SonarPlot";

/** The list's rows as Sonar blips; a row the toolbar's filters hide is a dimmed blip. */
export function sonarPoints(entries: ListEntry[], shownIds: ReadonlySet<string>): SonarPoint[] {
  return entries.map((e) => ({
    id: e.company_id,
    name: e.name,
    rank: e.rank,
    potential: e.score.potential,
    evidence: e.score.evidence,
    group: e.group,
    vertical: e.vertical ?? null,
    dimmed: !shownIds.has(e.company_id),
  }));
}
