// The scored blind set: the same level cards as the answer keys get, then each company side by side.
// It lives in the page's memory only and is gone on reload or navigation.
import { FileUp, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { PrecisionReport } from "../../contracts";
import { useT } from "../../i18n/messages";
import { ofN } from "../../lib/format";
import { Panel } from "../../ui/Panel";
import { LevelCards } from "./LevelCards";
import { precisionMessages } from "./messages";
import { orderedLevels, partnerRows } from "./model";
import { PartnerTable } from "./PartnerTable";
import { Figure, Rich } from "./Rich";

interface BlindResultProps {
  report: PrecisionReport;
  onClear(): void;
}

export function BlindResult({ report, onClear }: BlindResultProps) {
  const { t, tn } = useT(precisionMessages);
  const bodyRef = useRef<HTMLDivElement>(null);
  const rows = partnerRows(report.notes ?? []);
  const matched = rows.filter((row) => row.matched).length;

  // A new result lands below the fold: take the reader (and focus) to it.
  useEffect(() => {
    bodyRef.current?.focus();
  }, [report]);

  return (
    <Panel
      title={t("blindResultTitle")}
      icon={<FileUp size={16} strokeWidth={1.5} aria-hidden="true" />}
      meta={tn("blindCompanies", rows.length)}
      className="precision__full blind-result"
      actions={
        <button type="button" className="btn btn--ghost btn--sm" onClick={onClear}>
          <X size={14} strokeWidth={1.5} aria-hidden="true" />
          {t("clear")}
        </button>
      }
    >
      <div className="blind-result__body" ref={bodyRef} tabIndex={-1}>
        <p className="blind-result__matched">
          <Rich
            text={t("blindMatched")}
            values={{ count: <Figure>{ofN(matched, rows.length)}</Figure> }}
          />
        </p>
        <LevelCards levels={orderedLevels(report)} />
        {rows.length > 0 && <PartnerTable rows={rows} />}
      </div>
    </Panel>
  );
}
