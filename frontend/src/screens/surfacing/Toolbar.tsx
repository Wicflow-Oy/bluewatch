// Above the list: the group filter, the signal chips, the keyboard hints and (phones) the Sonar pill.
import { Radar } from "lucide-react";
import type { ListEntry } from "../../contracts";
import { useT } from "../../i18n/messages";
import { chipLabel } from "../../lib/labels";
import { useIsPhone } from "../../lib/media";
import { useMeta } from "../../lib/meta";
import { Segmented, type SegmentOption } from "../../ui/Segmented";
import { sonarMessages } from "../../ui/SonarPlot.messages";
import { Kbd } from "../../ui/States";
import { SIGNALS, type Filters, type GroupFilter, type Signal } from "./filters";
import { SURFACING_GROUPS } from "./groups";
import { surfacingMessages } from "./messages";

interface ToolbarProps {
  entries: ListEntry[];
  filters: Filters;
  onChange(filters: Filters): void;
  onOpenSonar(): void;
}

export function Toolbar({ entries, filters, onChange, onOpenSonar }: ToolbarProps) {
  const { t } = useT(surfacingMessages);
  const sonar = useT(sonarMessages);
  const meta = useMeta();
  const phone = useIsPhone();

  const groups: SegmentOption<GroupFilter>[] = [
    { value: "all", label: t("all"), count: entries.length },
    ...SURFACING_GROUPS.map((g) => ({
      value: g,
      label: meta.group(g),
      count: entries.filter((e) => e.group === g).length,
    })),
  ];

  const toggle = (signal: Signal) => {
    const signals = new Set(filters.signals);
    if (signals.has(signal)) signals.delete(signal);
    else signals.add(signal);
    onChange({ ...filters, signals });
  };

  return (
    <div className="surfacing__toolbar">
      <div className="surfacing__filters">
        <div className="surfacing__groups">
          <Segmented
            options={groups}
            value={filters.group}
            onChange={(group) => onChange({ ...filters, group })}
            label={t("groupFilter")}
            size={phone ? "sm" : "lg"}
          />
        </div>
        <span className="surfacing__divider" aria-hidden="true" />
        <div className="surfacing__signals" role="group" aria-label={t("signalFilter")}>
          {SIGNALS.map((signal) => {
            const count = entries.filter((e) => e.chip === signal).length;
            return (
              <button
                key={signal}
                type="button"
                className="chip-btn"
                aria-pressed={filters.signals.has(signal)}
                disabled={count === 0 && !filters.signals.has(signal)}
                onClick={() => toggle(signal)}
              >
                {chipLabel(signal)}
                <span className="ct">{count}</span>
              </button>
            );
          })}
        </div>
        <button
          type="button"
          className="btn btn--sm surfacing__sonar-pill"
          onClick={onOpenSonar}
          aria-haspopup="dialog"
        >
          <Radar aria-hidden="true" />
          {sonar.t("sonar")}
        </button>
      </div>
      <p className="surfacing__hints" aria-hidden="true">
        <Kbd>J</Kbd>
        <Kbd>K</Kbd>
        <span>{t("hintMove")}</span>
        <Kbd>↵</Kbd>
        <span>{t("hintOpen")}</span>
        <Kbd>Esc</Kbd>
        <span>{t("hintClose")}</span>
      </p>
    </div>
  );
}
