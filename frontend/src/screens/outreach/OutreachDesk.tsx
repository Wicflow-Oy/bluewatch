// The desk for one company: the stepper, the draft with its single next action, the unknowns the
// message closes and the audit trail. The company's card supplies the unknowns and the match state.
import { RotateCcw } from "lucide-react";
import { use, useCallback, useEffect, useState } from "react";
import type { DraftLanguage } from "../../api";
import type { Evidence } from "../../contracts";
import { load } from "../../data";
import { useLang } from "../../i18n/lang";
import { useT } from "../../i18n/messages";
import { usePreset } from "../../lib/preset";
import { useWorkspace } from "../../lib/workspace";
import { AuditTrail } from "../../ui/AuditTrail";
import { Panel } from "../../ui/Panel";
import { LoadingRegion, SkeletonLines } from "../../ui/States";
import { Stepper } from "../../ui/Stepper";
import { useToast } from "../../ui/Toast";
import { auditEntries } from "./auditEntries";
import { ClosesPanel, ClosesSkeleton, closesItemId } from "./ClosesPanel";
import { DeskUnavailable, DraftFailed, DraftRefused, NotAssessed, Unmatched } from "./DeskStates";
import type { DraftStatus } from "./DraftAction";
import { DraftPanel, DraftSkeleton } from "./DraftPanel";
import { outreachMessages, type OutreachT } from "./messages";
import { useDesk, type DeskControls, type DeskState } from "./useDesk";

const AFTER_APPROVAL: DraftStatus[] = ["approved", "sent", "blocked_demo", "replied"];
const AFTER_SEND: DraftStatus[] = ["sent", "blocked_demo", "replied"];

function stepsFor(state: DeskState, t: OutreachT) {
  const status = state.kind === "ready" ? (state.view.draft.status ?? "draft") : null;
  const reached = (after: DraftStatus[]) => status !== null && after.includes(status);
  const steps = [
    { id: "draft", label: t("step_draft"), done: status !== null && status !== "draft" },
    { id: "approve", label: t("step_approve"), done: reached(AFTER_APPROVAL) },
    { id: "send", label: t("step_send"), done: reached(AFTER_SEND) },
    { id: "reply", label: t("step_reply"), done: status === "replied" },
  ];
  const current = steps.find((s) => !s.done)?.id ?? "reply";
  return { steps, current };
}

/** Brings a "What this closes" item into view; on a phone it sits below the draft. */
function revealUnknown(evidenceId: string, focus: boolean): void {
  const item = document.getElementById(closesItemId(evidenceId));
  const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  item?.scrollIntoView({ block: "nearest", behavior: smooth ? "smooth" : "auto" });
  if (focus) item?.focus({ preventScroll: true });
}

interface OutreachDeskProps {
  companyId: string;
  /** The bridge the draft is about; without it, the company's best bridge or opportunity. */
  bridgeId?: string;
}

export function OutreachDesk({ companyId, bridgeId }: OutreachDeskProps) {
  const { t } = useT(outreachMessages);
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const toast = useToast();
  const card = use(load.card(companyId, mode, preset))?.data ?? null;
  const resolved = card?.company.resolution.state === "resolved";
  // The message starts in the reader's language; switching the interface later never rewrites a
  // draft someone may be about to approve.
  const uiLanguage = useLang();
  const [language, setLanguage] = useState<DraftLanguage>(uiLanguage);
  const onSent = useCallback(() => toast(t("sentToast"), "success"), [toast, t]);
  const desk = useDesk({ companyId, bridgeId, mode, language }, resolved, onSent);

  if (!card) return <NotAssessed />;

  return (
    <div className="outreach-desk">
      <div className="outreach-steps capsule">
        <Stepper {...stepsFor(desk.state, t)} />
        {resolved && (
          <button
            type="button"
            className="btn btn--subtle btn--sm"
            onClick={desk.startOver}
            disabled={desk.state.kind === "creating"}
          >
            <RotateCcw size={14} strokeWidth={1.5} aria-hidden="true" />
            <span>{t("startOver")}</span>
          </button>
        )}
      </div>
      {resolved ? (
        <DeskBody
          desk={desk}
          language={language}
          onLanguage={setLanguage}
          unknowns={card.ledger.unknowns ?? []}
        />
      ) : (
        <Unmatched company={card.company} />
      )}
    </div>
  );
}

interface DeskBodyProps {
  desk: DeskControls;
  language: DraftLanguage;
  onLanguage(language: DraftLanguage): void;
  unknowns: Evidence[];
}

function DeskBody({ desk, language, onLanguage, unknowns }: DeskBodyProps) {
  const text = useT(outreachMessages);
  const { t } = text;
  const { state } = desk;
  const replied = state.kind === "ready" && state.reply !== null;
  const firstAsked =
    state.kind === "ready" ? state.view.draft.questions?.[0]?.evidence_id : undefined;

  // The confirmed items may sit below the fold (on a phone, under the draft): bring them into view.
  useEffect(() => {
    if (replied && firstAsked) revealUnknown(firstAsked, false);
  }, [replied, firstAsked]);

  if (state.kind === "unavailable") return <DeskUnavailable />;
  if (state.kind === "failed") return <DraftFailed onRetry={desk.startOver} />;
  if (state.kind === "refused") return <DraftRefused message={state.message} />;

  const ready = state.kind === "ready" ? state : null;
  const fieldOf = (evidenceId: string) => unknowns.find((u) => u.id === evidenceId)?.field ?? null;

  return (
    <div className="outreach-grid">
      <div className="outreach-grid__main">
        {ready ? (
          <DraftPanel
            desk={ready}
            language={language}
            onLanguage={onLanguage}
            fieldOf={fieldOf}
            onShowUnknown={(evidenceId) => revealUnknown(evidenceId, true)}
            onApprove={desk.approve}
            onSend={desk.send}
            onReply={desk.reply}
          />
        ) : (
          <LoadingRegion label={t("preparingDraft")}>
            <DraftSkeleton />
          </LoadingRegion>
        )}
      </div>
      <div className="outreach-grid__side">
        {ready ? (
          <ClosesPanel
            questions={ready.view.draft.questions ?? []}
            unknowns={unknowns}
            confirmed={ready.reply?.confirmed ?? []}
          />
        ) : (
          <ClosesSkeleton />
        )}
        <Panel title={t("auditTitle")} meta={t("auditMeta")}>
          {ready ? (
            <AuditTrail
              entries={auditEntries(ready.view.draft.audit ?? [], text)}
              label={t("auditTitle")}
              empty={t("auditEmpty")}
            />
          ) : (
            <SkeletonLines lines={4} />
          )}
        </Panel>
      </div>
    </div>
  );
}

export function OutreachDeskSkeleton() {
  const { t } = useT(outreachMessages);
  return (
    <LoadingRegion label={t("loadingDesk")}>
      <div className="outreach-desk">
        <div className="outreach-steps capsule">
          <Stepper {...stepsFor({ kind: "creating" }, t)} />
        </div>
        <div className="outreach-grid">
          <div className="outreach-grid__main">
            <DraftSkeleton />
          </div>
          <div className="outreach-grid__side">
            <ClosesSkeleton />
            <Panel title={t("auditTitle")} meta={t("auditMeta")}>
              <SkeletonLines lines={4} />
            </Panel>
          </div>
        </div>
      </div>
    </LoadingRegion>
  );
}
