// The rail's hero, the night "Due next" card: the list's own dated steps plus the alert deadlines.
import { Suspense, use } from "react";
import type { Alert, ListEntry } from "../../contracts";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import { useWorkspace } from "../../lib/workspace";
import { shellMessages } from "../../shell/messages";
import { Boundary } from "../../ui/Boundary";
import { DueNextCard } from "../../ui/DueNextCard";
import { deadlineItems } from "./deadlines";
import { surfacingMessages } from "./messages";

export function RailDeadlines({ entries }: { entries: ListEntry[] }) {
  const { mode } = useWorkspace();
  // Alerts only add to the list's own deadlines: while they load, or if they fail, the card shows the list's.
  const own = <DueNext entries={entries} alerts={[]} />;
  return (
    <Boundary key={mode} fallback={own}>
      <Suspense fallback={own}>
        <DueNextWithAlerts entries={entries} />
      </Suspense>
    </Boundary>
  );
}

function DueNextWithAlerts({ entries }: { entries: ListEntry[] }) {
  const { mode } = useWorkspace();
  const alerts = use(load.alerts(mode)).data;
  return <DueNext entries={entries} alerts={alerts} />;
}

function DueNext({ entries, alerts }: { entries: ListEntry[]; alerts: Alert[] }) {
  const { t } = useT(surfacingMessages);
  const { tn } = useT(shellMessages);
  const meta = useMeta();
  const items = deadlineItems(entries, alerts, meta.today, {
    entryTitle: (company, action) => t("deadlineTitle", { company, action }),
    groupDetail: (n) => tn("listedCompanies", n),
  });
  return <DueNextCard items={items} today={meta.today} />;
}
