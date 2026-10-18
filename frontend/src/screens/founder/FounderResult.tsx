// One lookup's answer. The register decides which shape it takes: a company, a sole trader (nothing is
// shown), a company that no longer trades (its profile only), an ID the register doesn't know, an ID outside the recorded data while live lookups are off,
// or a register that couldn't answer.
import type { FounderResponse, Mode } from "../../api";
import type { Comparison } from "./compare";
import { CompareStrip } from "./CompareStrip";
import { FundingTiers } from "./FundingTiers";
import { Investors } from "./Investors";
import { NextSteps } from "./NextSteps";
import { Profile } from "./Profile";
import { Programmes } from "./Programmes";
import {
  NoLongerTrading,
  NotInRegister,
  NotRecorded,
  RegisterDown,
  SoleTrader,
} from "./ResultStates";
import { ShareRow } from "./ShareRow";

interface FounderResultProps {
  response: FounderResponse;
  /** The answer came from the recorded data because the API could not be reached. */
  recorded: boolean;
  comparison: Comparison | null;
  mode: Mode;
  today: string;
  onRetry(): void;
}

export function FounderResult({
  response,
  recorded,
  comparison,
  mode,
  today,
  onRetry,
}: FounderResultProps) {
  const { lookup, view } = response;
  if (lookup.natural_person) return <SoleTrader />;
  if (!view) {
    // Live lookups are off, so only the recorded data was searched: a setting, which retrying can't change.
    if (lookup.recorded_only) return <NotRecorded companyId={lookup.company_id} />;
    if (lookup.status.state !== "unavailable")
      return <NotInRegister companyId={lookup.company_id} />;
    return (
      <RegisterDown country={lookup.country} detail={lookup.status.detail} onRetry={onRetry} />
    );
  }
  if (lookup.closed) {
    return (
      <div className="founder-result">
        <Profile profile={view.profile} lookup={lookup} recorded={recorded} />
        <NoLongerTrading message={lookup.message} />
      </div>
    );
  }
  return (
    <div className="founder-result">
      {comparison && <CompareStrip comparison={comparison} mode={mode} />}
      <Profile profile={view.profile} lookup={lookup} recorded={recorded} />
      <NextSteps steps={view.next_30_days ?? []} mode={mode} today={today} />
      <Investors investors={view.investors ?? []} />
      <FundingTiers tiers={view.tiers ?? []} mode={mode} researched={Boolean(lookup.company_id)} />
      <Programmes
        programmes={view.programmes ?? []}
        name={view.profile.name}
        mode={mode}
        today={today}
      />
      {mode === "apelago" && <ShareRow key={view.profile.id} />}
    </div>
  );
}
