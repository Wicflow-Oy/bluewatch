// The report's provenance beside the title: what the answer keys are, whether the rules are frozen,
// and which rules version produced the numbers.
import { BookOpen, Lock, LockOpen } from "lucide-react";
import type { ReactNode } from "react";
import type { PrecisionReport } from "../../contracts";
import { useT } from "../../i18n/messages";
import { formatStamp } from "../../lib/format";
import { Chip } from "../../ui/Chip";
import { Tooltip } from "../../ui/Tooltip";
import { precisionMessages } from "./messages";

export function HeaderChips({ report }: { report: PrecisionReport }) {
  const { t } = useT(precisionMessages);
  return (
    <div className="precision__chips">
      {report.reference && (
        <TipChip tip={capitalise(report.reference)}>
          <Chip icon={<BookOpen size={12} strokeWidth={1.5} aria-hidden="true" />}>
            {t("answerKeysChip")}
          </Chip>
        </TipChip>
      )}
      {report.frozen_at ? (
        <Chip tone="teal" icon={<Lock size={12} strokeWidth={1.5} aria-hidden="true" />}>
          {t("frozen")} <span className="mono">{formatStamp(report.frozen_at)}</span>
        </Chip>
      ) : (
        <TipChip tip={t("notFrozenTip")}>
          <Chip tone="amber" icon={<LockOpen size={12} strokeWidth={1.5} aria-hidden="true" />}>
            {t("notFrozen")}
          </Chip>
        </TipChip>
      )}
      <TipChip tip={t("rulesHashTip")}>
        <Chip>
          <span className="mono">{report.rules_hash}</span>
        </Chip>
      </TipChip>
    </div>
  );
}

/** A chip with a tooltip that keyboard and touch users can open too. */
function TipChip({ tip, children }: { tip: string; children: ReactNode }) {
  return (
    <Tooltip content={tip} placement="bottom">
      <button type="button" className="precision__tip-chip">
        {children}
      </button>
    </Tooltip>
  );
}

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
