// The venture card of the open row, in the card sheet over the list. Opening and closing morph between the
// row and the sheet (TIDEPOOL-SYSTEM.md 4.1).
import { lazy, Suspense, useEffect, useState } from "react";
import type { ListEntry } from "../../contracts";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { listRow, morph, sheetPanel } from "../../lib/motion";
import { usePreset } from "../../lib/preset";
import { navigate, navigateNow, type CardTab } from "../../lib/router";
import { useWorkspace } from "../../lib/workspace";
import { Drawer } from "../../ui/Drawer";
import { DetailSkeleton } from "../common/ScreenSkeleton";
import { surfacingMessages } from "./messages";

// The card is its own chunk: the list paints first, then the chunk loads while the browser is idle,
// so opening a row only waits for the card's data.
const cardChunk = () => import("../card");
const VentureCardView = lazy(() => cardChunk().then((m) => ({ default: m.VentureCardView })));

function whenIdle(run: () => void): () => void {
  if ("requestIdleCallback" in window) {
    const id = window.requestIdleCallback(run, { timeout: 2000 });
    return () => window.cancelIdleCallback(id);
  }
  const id = setTimeout(run, 500);
  return () => clearTimeout(id);
}

interface CardDrawerProps {
  entries: ListEntry[];
  companyId?: string;
  tab?: CardTab;
}

export function CardDrawer({ entries, companyId, tab }: CardDrawerProps) {
  const { t } = useT(surfacingMessages);
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  useEffect(() => whenIdle(() => void cardChunk().catch(() => undefined)), []);
  // Keep the last card mounted while the sheet closes.
  const [shownId, setShownId] = useState(companyId);
  if (companyId && companyId !== shownId) setShownId(companyId);
  // Ask for the card now, not once its chunk has loaded; the card view reads the same memoised load.
  if (companyId) void load.card(companyId, mode, preset).catch(() => undefined);
  const name = entries.find((e) => e.company_id === shownId)?.name;
  const close = () =>
    morph(
      "bw-card",
      sheetPanel(),
      () => navigateNow({ name: "surfacing" }),
      () => (shownId ? listRow(shownId) : null),
    );
  return (
    <Drawer
      open={companyId !== undefined}
      onClose={close}
      label={name ? t("cardOf", { name }) : t("card")}
      variant="card"
    >
      {shownId && (
        <Suspense fallback={<DetailSkeleton />}>
          <VentureCardView
            companyId={shownId}
            tab={tab ?? "overview"}
            layout="drawer"
            onTabChange={(next) => navigate({ name: "surfacing", companyId: shownId, tab: next })}
            onClose={close}
          />
        </Suspense>
      )}
    </Drawer>
  );
}
