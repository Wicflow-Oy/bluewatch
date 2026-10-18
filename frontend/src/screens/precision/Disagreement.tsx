// Where we disagree: one confusion matrix per level with answer keys, answer key down, ours across.
import { Grid3x3 } from "lucide-react";
import { useState } from "react";
import type { LevelAgreement } from "../../contracts";
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import { Panel } from "../../ui/Panel";
import { EmptyState } from "../../ui/States";
import { TabPanel, Tabs } from "../../ui/Tabs";
import { precisionMessages } from "./messages";
import type { LevelKey } from "./model";
import { ConfusionMatrix } from "./ConfusionMatrix";

export function Disagreement({ levels }: { levels: LevelAgreement[] }) {
  const { t } = useT(precisionMessages);
  const meta = useMeta();
  const scored = levels.filter((level) => level.n > 0 && level.confusion);
  const [selected, setSelected] = useState<LevelKey | undefined>(scored[0]?.key);
  // On a phone the matrix waits behind a disclosure; on wider screens it is always shown.
  const [shown, setShown] = useState(false);
  const level = scored.find((l) => l.key === selected) ?? scored[0];

  return (
    <Panel
      title={t("disagreeTitle")}
      icon={<Grid3x3 size={16} strokeWidth={1.5} aria-hidden="true" />}
      className="precision__order-1"
      flush
    >
      {level ? (
        <>
          <div className="matrix-panel__tabs">
            <Tabs
              tabs={scored.map((l) => ({ id: l.key, label: meta.level(l.key) }))}
              value={level.key}
              onChange={setSelected}
              label={t("readinessLevel")}
              idPrefix="precision-matrix"
              size="sm"
            />
          </div>
          <TabPanel idPrefix="precision-matrix" tab={level.key}>
            <div className="matrix-panel__body">
              <button
                type="button"
                className="btn btn--sm matrix-panel__toggle"
                aria-expanded={shown}
                onClick={() => setShown((v) => !v)}
              >
                {t(shown ? "hideMatrix" : "showMatrix")}
              </button>
              <div className="matrix-panel__matrix" data-shown={shown}>
                <ConfusionMatrix confusion={level.confusion ?? {}} label={meta.level(level.key)} />
              </div>
              <p className="matrix-panel__caption">{t("matrixCaption")}</p>
            </div>
          </TabPanel>
        </>
      ) : (
        <EmptyState compact title={t("noMatrixTitle")}>
          {t("noMatrixBody")}
        </EmptyState>
      )}
    </Panel>
  );
}
