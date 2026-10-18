// Every other bridge as a compact row. Most generated bridges are only "possible" (a programme that
// fits what is known), so the panel opens on the verified and probable ones and counts the rest.
import { useMemo, useState } from "react";
import type { Bridge } from "../../contracts";
import { useT } from "../../i18n/messages";
import type { BridgeType } from "../../lib/labels";
import { vars } from "../../lib/motion";
import { EmptyState } from "../../ui/States";
import { BridgeFilters, type Strength, type TypeFilter } from "./BridgeFilters";
import { BridgeRow } from "./BridgeRow";
import { hiddenName } from "./hideNames";
import { bridgesMessages } from "./messages";
import { byDeadline, isStrong } from "./order";

/** Enough rows to scan in one screen; the rest are one click away. */
const PAGE_SIZE = 20;

interface OtherBridgesProps {
  bridges: Bridge[];
  today: string;
  /** Each row shows its company as a description from register data instead of the name. */
  hideNames: boolean;
}

export function OtherBridges({ bridges, today, hideNames }: OtherBridgesProps) {
  const { t, tn } = useT(bridgesMessages);
  const [strength, setStrength] = useState<Strength>("strong");
  const [type, setType] = useState<TypeFilter>("all");
  const [showAll, setShowAll] = useState(false);

  const sorted = useMemo(() => [...bridges].sort(byDeadline), [bridges]);
  const strong = sorted.filter(isStrong);
  const kept = strength === "strong" ? strong : sorted;
  const rows = type === "all" ? kept : kept.filter((b) => b.type === type);
  const visible = showAll ? rows : rows.slice(0, PAGE_SIZE);
  const hiddenPossible = sorted.length - strong.length;
  const truncated = rows.length > visible.length;
  const filteredOut = strength === "strong" && rows.length > 0 && hiddenPossible > 0;

  const chooseStrength = (next: Strength) => {
    setStrength(next);
    setType("all");
    setShowAll(false);
  };
  const chooseType = (next: TypeFilter) => {
    setType(next);
    setShowAll(false);
  };

  return (
    <section className="bridge-others" aria-labelledby="bridge-others-title">
      <header className="bridge-others__head">
        <h2 className="t-title" id="bridge-others-title">
          {t("otherBridges")}
        </h2>
        <span className="bridge-others__count mono">{sorted.length}</span>
      </header>
      <BridgeFilters
        strength={strength}
        strongCount={strong.length}
        totalCount={sorted.length}
        onStrength={chooseStrength}
        type={type}
        typeCounts={countTypes(kept)}
        typesTotal={kept.length}
        onType={chooseType}
      />

      {rows.length === 0 ? (
        <EmptyState compact title={strength === "strong" ? t("noneStrong") : t("noneAtAll")}>
          {strength === "strong" && hiddenPossible > 0
            ? tn("possibleUnderAll", hiddenPossible)
            : t("onlyBridge")}
        </EmptyState>
      ) : (
        <ul className="bridge-others__list">
          {visible.map((b, i) => (
            <li key={b.id} className="stagger-in" style={vars({ "--i": i })}>
              <BridgeRow
                bridge={b}
                today={today}
                companyName={hideNames ? hiddenName(b) : undefined}
              />
            </li>
          ))}
        </ul>
      )}

      {truncated ? (
        <p className="bridge-others__more">
          <button type="button" className="btn btn--sm" onClick={() => setShowAll(true)}>
            {t("showAllN", { n: rows.length })}
          </button>
        </p>
      ) : (
        filteredOut && (
          <p className="bridge-others__more">
            <span>{tn("possibleHidden", hiddenPossible)}</span>
            <button
              type="button"
              className="btn btn--sm btn--ghost"
              onClick={() => chooseStrength("all")}
            >
              {t("showAll")}
            </button>
          </p>
        )
      )}
    </section>
  );
}

function countTypes(bridges: Bridge[]): [BridgeType, number][] {
  const counts = new Map<BridgeType, number>();
  for (const b of bridges) counts.set(b.type, (counts.get(b.type) ?? 0) + 1);
  return [...counts].sort((a, b) => b[1] - a[1]);
}
