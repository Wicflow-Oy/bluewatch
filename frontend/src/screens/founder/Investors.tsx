// Investors whose stage, thesis and geography fit, best first; the rest stay behind "Show more".
import { Banknote } from "lucide-react";
import { useState } from "react";
import type { InvestorMatch } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { Chip } from "../../ui/Chip";
import { Panel } from "../../ui/Panel";
import { founderMessages } from "./messages";

const SHOWN = 6;

export function Investors({ investors }: { investors: InvestorMatch[] }) {
  const { t, tn } = useT(founderMessages);
  const [expanded, setExpanded] = useState(false);
  const fitting = investors.filter((investor) => investor.when !== "not_a_fit");
  const shown = expanded ? fitting : fitting.slice(0, SHOWN);
  const hidden = fitting.length - shown.length;
  return (
    <Panel
      className="founder-result__investors"
      icon={<Banknote size={16} strokeWidth={1.5} aria-hidden="true" />}
      title={t("investorsTitle")}
      meta={<span className="mono">{tn("matches", fitting.length)}</span>}
    >
      {fitting.length === 0 ? (
        <p className="muted">{t("noInvestors")}</p>
      ) : (
        <ul className="founder-list">
          {shown.map((investor) => (
            <InvestorRow key={investor.investor_id} investor={investor} />
          ))}
        </ul>
      )}
      {hidden > 0 && (
        <button
          type="button"
          className="btn btn--ghost btn--sm founder-more"
          onClick={() => setExpanded(true)}
        >
          {t("showMore", { n: hidden })}
        </button>
      )}
    </Panel>
  );
}

function InvestorRow({ investor }: { investor: InvestorMatch }) {
  const { t } = useT(founderMessages);
  return (
    <li className="founder-list__row">
      <div className="founder-list__text">
        <span className="founder-list__name">{investor.name}</span>
        <span className="founder-list__detail">{humanText(investor.fit_label)}</span>
      </div>
      {investor.when === "now" ? (
        <Chip tone="blue" dot>
          {t("fitsNow")}
        </Chip>
      ) : (
        <Chip tone="outline" dot>
          {t("later")}
        </Chip>
      )}
    </li>
  );
}
