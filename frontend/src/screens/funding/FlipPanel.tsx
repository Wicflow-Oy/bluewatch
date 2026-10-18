// The SBEP call 4 flip: the same call read for a Finnish and a Norwegian company. Nothing here is
// special-cased: both sides are the catalogue's own tier rows, worded for the current workspace.
import { ArrowRight } from "lucide-react";
import type { Mode } from "../../api";
import type { FundingInstrument, FundingTierRow } from "../../contracts";
import { useT } from "../../i18n/messages";
import { hostOf } from "../../lib/format";
import { countryName } from "../../lib/labels";
import { useMeta } from "../../lib/meta";
import { CountryCode, TierChip } from "../../ui/Chip";
import { Deadline } from "../../ui/Deadline";
import { Panel } from "../../ui/Panel";
import { RuleLine } from "../../ui/RuleLine";
import { SourceChip } from "../../ui/SourceChip";
import { ErrorState } from "../../ui/States";
import { TierNotes } from "../../ui/TierGroup";
import { FLIP_LEFT_ID, FLIP_RIGHT_ID, type Flip } from "./catalogue";
import { fundingMessages } from "./messages";

export function FlipPanel({ flip, mode }: { flip: Flip; mode: Mode }) {
  const { t } = useT(fundingMessages);
  const { today } = useMeta();
  const { call } = flip;
  const host = hostOf(call?.url);
  return (
    <Panel title={t("flipTitle")} className="flip" labelledBy="funding-flip">
      <p className="flip__sub">{t("flipNote")}</p>
      <div className="flip__grid">
        <FlipCard companyId={FLIP_LEFT_ID} row={flip.left} call={call} mode={mode} />
        <div className="flip__between">
          <span className="flip__arrow" aria-hidden="true">
            <ArrowRight size={16} strokeWidth={1.75} />
          </span>
          <p className="flip__same">{t("sameCall")}</p>
          {call?.deadline && <Deadline date={call.deadline} today={today} />}
        </div>
        <FlipCard companyId={FLIP_RIGHT_ID} row={flip.right} call={call} mode={mode} />
      </div>
      {call?.url && host && (
        <footer className="flip__footer">
          <SourceChip
            index={1}
            source={{ label: t("callPage", { host }), url: call.url, deadline: call.deadline }}
          />
          <span className="flip__call">{call.name}</span>
        </footer>
      )}
    </Panel>
  );
}

interface FlipCardProps {
  companyId: string;
  row: FundingTierRow | null;
  call: FundingInstrument | null;
  mode: Mode;
}

function FlipCard({ companyId, row, call, mode }: FlipCardProps) {
  const { t } = useT(fundingMessages);
  const country = row?.country ?? companyId.split(":")[0];
  const overline = (
    <p className="flip-card__country overline">
      {countryName(country)}
      <CountryCode code={country} />
    </p>
  );
  if (!row) {
    return (
      <div className="flip-card flip-card--missing hatch-frame hatch-frame--red">
        {overline}
        <ErrorState compact title={t("flipSideFailedTitle")}>
          {t("flipSideFailedBody")}
        </ErrorState>
      </div>
    );
  }
  return (
    <article className="flip-card inset">
      {overline}
      <h3 className="flip-card__name">{row.name}</h3>
      <div className="flip-card__tier">
        <TierChip tier={row.tier} mode={mode} />
      </div>
      <RuleLine rule={row.deciding_rule} source={call?.url} verified={row.rule_verified} />
      <TierNotes
        rule={row.deciding_rule}
        unknownReason={row.unknown_reason}
        upgradePath={row.upgrade_path}
      />
    </article>
  );
}
