// Phones: the Sonar in a bottom sheet. Choosing a blip closes the sheet, then opens the card.
import { X } from "lucide-react";
import type { ListEntry } from "../../contracts";
import { useT } from "../../i18n/messages";
import { shellMessages } from "../../shell/messages";
import { Drawer } from "../../ui/Drawer";
import { SonarPlot } from "../../ui/SonarPlot";
import { sonarMessages } from "../../ui/SonarPlot.messages";
import { sonarPoints } from "./sonarPoints";

interface SonarSheetProps {
  open: boolean;
  entries: ListEntry[];
  /** The rows the toolbar's filters let through; the other blips are dimmed. */
  shownIds: ReadonlySet<string>;
  onClose(): void;
  onChoose(companyId: string): void;
}

export function SonarSheet({ open, entries, shownIds, onClose, onChoose }: SonarSheetProps) {
  const { t } = useT(sonarMessages);
  const shell = useT(shellMessages);
  return (
    <Drawer open={open} onClose={onClose} label={t("sonar")} variant="sheet">
      <div className="sonar-sheet">
        <header className="sonar-sheet__head">
          <h2 className="sonar-sheet__title">{t("sonar")}</h2>
          <span className="sonar-sheet__aux mono">{t("sonarAux", { n: entries.length })}</span>
          <button
            type="button"
            className="icon-btn"
            onClick={onClose}
            aria-label={shell.t("close")}
          >
            <X aria-hidden="true" />
          </button>
        </header>
        <SonarPlot points={sonarPoints(entries, shownIds)} onSelect={onChoose} size="mini" />
      </div>
    </Drawer>
  );
}
