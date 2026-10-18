// The pipeline, the ranked list and the selected plan: side by side on wider screens, and on a phone a
// list whose rows open the plan in a full-screen sheet.
import { X } from "lucide-react";
import { useId, useState } from "react";
import type { ContactPlan } from "../../contracts";
import { useT } from "../../i18n/messages";
import { useIsPhone } from "../../lib/media";
import { shellMessages } from "../../shell/messages";
import { Chip } from "../../ui/Chip";
import { Drawer } from "../../ui/Drawer";
import { Panel } from "../../ui/Panel";
import { scoutMessages } from "./messages";
import { Pipeline } from "./Pipeline";
import { projectTitle } from "./plan";
import { PlanDetail } from "./PlanDetail";
import { PlanList } from "./PlanList";

interface ScoutBoardProps {
  plans: ContactPlan[];
  /** The live service didn't answer and the recorded plans are shown. */
  demoData: boolean;
}

export function ScoutBoard({ plans, demoData }: ScoutBoardProps) {
  const { t, tn } = useT(scoutMessages);
  const shell = useT(shellMessages);
  const isPhone = useIsPhone();
  const [selectedId, setSelectedId] = useState(plans[0].project_id);
  const [sheetOpen, setSheetOpen] = useState(false);
  const titleId = useId();
  const selected = plans.find((p) => p.project_id === selectedId) ?? plans[0];

  const select = (id: string) => {
    setSelectedId(id);
    if (isPhone) setSheetOpen(true);
  };

  return (
    <>
      <Pipeline plans={plans} />
      <div className="scout__board">
        <Panel
          className="scout__list"
          flush
          title={t("rankedTeams")}
          meta={tn("plans", plans.length)}
          actions={demoData && <Chip>{shell.t("demoData")}</Chip>}
        >
          <PlanList
            plans={plans}
            selectedId={isPhone && !sheetOpen ? null : selectedId}
            onSelect={select}
          />
        </Panel>
        {!isPhone && (
          <Panel className="scout__detail">
            <PlanDetail plan={selected} titleId={titleId} />
          </Panel>
        )}
      </div>
      {isPhone && (
        <Drawer open={sheetOpen} onClose={() => setSheetOpen(false)} label={projectTitle(selected)}>
          <div className="scout-sheet__bar">
            <span className="scout-sheet__title">{projectTitle(selected)}</span>
            <button
              type="button"
              className="icon-btn scout-sheet__close"
              onClick={() => setSheetOpen(false)}
              aria-label={shell.t("close")}
            >
              <X size={16} strokeWidth={1.5} aria-hidden="true" />
            </button>
          </div>
          <div className="scout-sheet__body">
            <PlanDetail plan={selected} titleId={titleId} />
          </div>
        </Drawer>
      )}
    </>
  );
}
