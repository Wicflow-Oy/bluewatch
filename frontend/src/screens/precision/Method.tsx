// How the numbers were made, in the report's own words. The first notes say what was compared and how;
// the per-level detail behind the cards waits behind "Show all".
import { BookOpen } from "lucide-react";
import { useState } from "react";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { Panel } from "../../ui/Panel";
import { precisionMessages } from "./messages";

const FIRST_NOTES = 3;

export function Method({ notes }: { notes: string[] }) {
  const { t, tn } = useT(precisionMessages);
  const [all, setAll] = useState(false);
  const shown = all ? notes : notes.slice(0, FIRST_NOTES);
  return (
    <Panel
      title={t("methodTitle")}
      icon={<BookOpen size={16} strokeWidth={1.5} aria-hidden="true" />}
      className="precision__order-4"
    >
      <ul className="method">
        <li>{t("matchedBy")}</li>
        {shown.map((note) => (
          <li key={note}>{humanText(note)}</li>
        ))}
      </ul>
      {notes.length > FIRST_NOTES && (
        <button
          type="button"
          className="btn btn--subtle btn--sm method__more"
          aria-expanded={all}
          onClick={() => setAll((v) => !v)}
        >
          {all ? t("showFewerNotes") : tn("showAllNotes", notes.length)}
        </button>
      )}
    </Panel>
  );
}
