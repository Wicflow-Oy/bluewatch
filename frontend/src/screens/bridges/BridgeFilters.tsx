import { useT } from "../../i18n/messages";
import { bridgeType, type BridgeType } from "../../lib/labels";
import { Segmented } from "../../ui/Segmented";
import { bridgesMessages } from "./messages";

export type Strength = "strong" | "all";
export type TypeFilter = BridgeType | "all";

interface BridgeFiltersProps {
  strength: Strength;
  strongCount: number;
  totalCount: number;
  onStrength(next: Strength): void;
  type: TypeFilter;
  /** Each type with its count among the bridges the strength filter keeps, largest first. */
  typeCounts: [BridgeType, number][];
  typesTotal: number;
  onType(next: TypeFilter): void;
}

/** How sure (verified and probable, or all) and which bridge type. */
export function BridgeFilters({
  strength,
  strongCount,
  totalCount,
  onStrength,
  type,
  typeCounts,
  typesTotal,
  onType,
}: BridgeFiltersProps) {
  const { t } = useT(bridgesMessages);
  return (
    <div className="bridge-others__filters">
      <Segmented
        size="sm"
        label={t("confidence")}
        value={strength}
        onChange={onStrength}
        options={[
          { value: "strong", label: t("strongOnly"), count: strongCount },
          { value: "all", label: t("all"), count: totalCount },
        ]}
      />
      <label className="bridge-others__type">
        <span className="sr-only">{t("type")}</span>
        <select
          className="select bridge-others__select"
          value={type}
          onChange={(e) => onType(e.target.value as TypeFilter)}
        >
          <option value="all">{t("allTypes", { n: typesTotal })}</option>
          {typeCounts.map(([key, n]) => (
            <option key={key} value={key}>
              {t("typeCount", { label: bridgeType(key).label, n })}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
