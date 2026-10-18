// The bridge's one action. A draft can only be prepared for a company matched to its register record:
// the outreach desk would refuse anything less, so the button says why instead of failing later.
import { FilePenLine, ShieldAlert } from "lucide-react";
import { Suspense, use, useId } from "react";
import type { Bridge } from "../../contracts";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { setOutreachTarget } from "../../lib/handoff";
import { usePreset } from "../../lib/preset";
import { navigate } from "../../lib/router";
import { useWorkspace } from "../../lib/workspace";
import { Boundary } from "../../ui/Boundary";
import { bridgesMessages } from "./messages";

type Blocker = "researchTeam" | "notMatched" | "notChecked";

export function DraftAction({ bridge }: { bridge: Bridge }) {
  const companyId = bridge.company.company_id;
  if (bridge.company.kind === "research_group") return <DraftButton blockedBy="researchTeam" />;
  if (!companyId) return <DraftButton blockedBy="notMatched" />;
  return (
    <Boundary fallback={<DraftButton blockedBy="notChecked" />}>
      <Suspense fallback={<DraftButton blockedBy={null} pending />}>
        <MatchedDraft companyId={companyId} bridgeId={bridge.id} />
      </Suspense>
    </Boundary>
  );
}

function MatchedDraft({ companyId, bridgeId }: { companyId: string; bridgeId: string }) {
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const rows = use(load.companies(mode, preset)).data;
  const resolved = rows.find((r) => r.id === companyId)?.resolution === "resolved";
  if (!resolved) return <DraftButton blockedBy="notMatched" />;
  return (
    <DraftButton
      blockedBy={null}
      onPrepare={() => {
        setOutreachTarget({ companyId, bridgeId });
        navigate({ name: "outreach" });
      }}
    />
  );
}

interface DraftButtonProps {
  /** Why no draft can be prepared; null when nothing blocks it. */
  blockedBy: Blocker | null;
  pending?: boolean;
  onPrepare?(): void;
}

function DraftButton({ blockedBy, pending = false, onPrepare }: DraftButtonProps) {
  const { t } = useT(bridgesMessages);
  const reasonId = useId();
  const unavailable = blockedBy !== null || pending;
  return (
    <div className="bridge-draft">
      <button
        type="button"
        className="btn btn--primary btn--lg"
        // aria-disabled keeps the button focusable, so keyboard users reach the reason too.
        aria-disabled={unavailable}
        aria-describedby={blockedBy ? reasonId : undefined}
        aria-busy={pending}
        onClick={unavailable ? undefined : onPrepare}
      >
        <FilePenLine size={16} strokeWidth={1.75} aria-hidden="true" />
        {t("prepareDraft")}
      </button>
      {blockedBy && (
        <p className="bridge-draft__blocked" id={reasonId}>
          <ShieldAlert size={14} strokeWidth={1.75} aria-hidden="true" />
          {t(blockedBy)}
        </p>
      )}
    </div>
  );
}
