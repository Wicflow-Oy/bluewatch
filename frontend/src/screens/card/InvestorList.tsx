// Investors ranked for this company, as capsule rows. A row opens to the reasons and caveats; not-a-fit investors stay
// hidden until asked for, so the list reads as signal.
import { ChevronDown } from "lucide-react";
import { useState } from "react";
import type { InvestorMatch } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText, levelText } from "../../lib/format";
import { useMeta } from "../../lib/meta";
import { vars } from "../../lib/motion";
import { InvestorWhenChip } from "../../ui/NextStepList";
import { Toggle } from "../../ui/Toggle";
import { cardMessages } from "./messages";

type CardKey = keyof typeof cardMessages.en;

const CHECKED_KEYS: Partial<Record<string, CardKey>> = {
  read: "checked_read",
  "read+snippet": "checked_read_snippet",
  snippet: "checked_snippet",
  "name-only": "checked_name_only",
};

function InvestorRow({ investor, index }: { investor: InvestorMatch; index: number }) {
  const { t } = useT(cardMessages);
  const { mode } = useMeta();
  const [open, setOpen] = useState(false);
  const detailId = `investor-${investor.investor_id}`;
  const why = investor.why ?? [];
  const caveats = investor.caveats ?? [];
  const hasDetail = why.length + caveats.length > 0;
  const { verification } = investor;
  const checkedKey = verification ? CHECKED_KEYS[verification] : undefined;
  const checked = checkedKey
    ? t(checkedKey)
    : verification
      ? humanText(verification)
      : t("checkedNotStated");
  return (
    <li className="investor capsule-row stagger-in" style={vars({ "--i": index })}>
      <button
        type="button"
        className="investor__row"
        aria-expanded={open}
        aria-controls={detailId}
        disabled={!hasDetail}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="investor__rank mono">{String(investor.rank).padStart(2, "0")}</span>
        <span className="investor__name">{investor.name}</span>
        <span className="investor__when">
          {investor.when && <InvestorWhenChip when={investor.when} />}
        </span>
        <span className="investor__fit">{humanText(investor.fit_label)}</span>
        <span className="investor__checked">{checked}</span>
        {hasDetail && (
          <ChevronDown
            size={14}
            strokeWidth={1.5}
            className="investor__chevron"
            aria-hidden="true"
          />
        )}
      </button>
      {open && (
        <ul className="investor__detail" id={detailId}>
          {why.map((line) => (
            <li key={line}>{levelText(humanText(line), mode)}</li>
          ))}
          {caveats.map((line) => (
            <li key={line} className="investor__caveat">
              {t("caveat", { text: levelText(humanText(line), mode) })}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function InvestorList({ investors }: { investors: InvestorMatch[] }) {
  const { t } = useT(cardMessages);
  const [showNotAFit, setShowNotAFit] = useState(false);
  const ranked = [...investors].sort((a, b) => a.rank - b.rank);
  const notAFit = ranked.filter((i) => i.when === "not_a_fit").length;
  const visible = showNotAFit ? ranked : ranked.filter((i) => i.when !== "not_a_fit");
  return (
    <div className="investors">
      <div className="investors__head" aria-hidden="true">
        <span>#</span>
        <span>{t("col_investor")}</span>
        <span>{t("col_when")}</span>
        <span>{t("col_fit")}</span>
        <span>{t("col_checked")}</span>
      </div>
      <ul className="investors__list">
        {visible.map((investor, i) => (
          <InvestorRow key={investor.investor_id} investor={investor} index={i} />
        ))}
      </ul>
      {notAFit > 0 && (
        <div className="investors__toggle">
          <Toggle
            checked={showNotAFit}
            onChange={setShowNotAFit}
            label={t("showNotAFit", { n: notAFit })}
          />
        </div>
      )}
    </div>
  );
}
