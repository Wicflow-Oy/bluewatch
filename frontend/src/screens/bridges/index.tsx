// Bridges: a dated, two-sided reason for a company to act now, with one action. The open bridge is the
// one in the URL, else the surest one with the soonest deadline.
import { Suspense, use, useEffect, useMemo, useRef } from "react";
import type { Mode } from "../../api";
import type { Bridge } from "../../contracts";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import { useWorkspace } from "../../lib/workspace";
import { Boundary } from "../../ui/Boundary";
import { Toggle } from "../../ui/Toggle";
import { BridgeHero } from "./BridgeHero";
import { BridgesHeader } from "./BridgesHeader";
import { aliasFor, useHideNames } from "./hideNames";
import { bridgesMessages } from "./messages";
import { byStrength, isStrong } from "./order";
import { OtherBridges } from "./OtherBridges";
import { BridgeNotHere, BridgesSkeleton, BridgesUnavailable, NoBridges } from "./States";
import "./Bridges.css";

export interface BridgesScreenProps {
  /** The bridge open in detail. */
  bridgeId?: string;
}

export function BridgesScreen({ bridgeId }: BridgesScreenProps) {
  const { mode } = useWorkspace();
  return (
    <Boundary key={mode} fallback={<BridgesUnavailable />}>
      <Suspense fallback={<BridgesSkeleton />}>
        <BridgesPage bridgeId={bridgeId} mode={mode} />
      </Suspense>
    </Boundary>
  );
}

function inWorkspace(bridge: Bridge, mode: Mode): boolean {
  return !bridge.mode || bridge.mode === mode || bridge.mode === "both";
}

/** null: the URL names a bridge this workspace doesn't have. */
function pickHero(bridges: Bridge[], bridgeId: string | undefined): Bridge | null {
  if (bridgeId !== undefined) return bridges.find((b) => b.id === bridgeId) ?? null;
  return [...bridges].sort(byStrength)[0] ?? null;
}

function BridgesPage({ bridgeId, mode }: { bridgeId?: string; mode: Mode }) {
  const { t, tn } = useT(bridgesMessages);
  const meta = useMeta();
  const loaded = use(load.bridges(mode));
  const bridges = useMemo(() => loaded.data.filter((b) => inWorkspace(b, mode)), [loaded, mode]);
  const [hideNames, setHideNames] = useHideNames();
  const hero = pickHero(bridges, bridgeId);
  const others = hero ? bridges.filter((b) => b.id !== hero.id) : bridges;

  // A row opens its bridge in the hero, so bring the hero into view.
  const pageRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    pageRef.current?.scrollIntoView({ block: "start" });
  }, [hero?.id]);

  const toggle = bridges.length > 0 && (
    <Toggle
      checked={hideNames}
      onChange={setHideNames}
      label={t("hideNames")}
      hint={t("hideNamesHint")}
    />
  );

  return (
    <div className="page bridges" ref={pageRef}>
      <BridgesHeader
        actions={toggle}
        meta={
          bridges.length > 0 && [
            <span key="n">{tn("metaBridges", bridges.length)}</span>,
            <span key="strong">{t("metaStrong", { n: bridges.filter(isStrong).length })}</span>,
          ]
        }
      />
      {bridges.length === 0 ? (
        <NoBridges />
      ) : (
        <div className="bridges__stack">
          {hero ? (
            <div key={hero.id} className="bridges__hero">
              <BridgeHero
                bridge={hero}
                today={meta.today}
                alias={aliasFor(hero, hideNames)}
                recorded={loaded.origin === "demo"}
              />
            </div>
          ) : (
            <BridgeNotHere mode={mode} />
          )}
          <OtherBridges bridges={others} today={meta.today} hideNames={hideNames} />
        </div>
      )}
    </div>
  );
}
