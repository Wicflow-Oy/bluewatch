// The outreach desk: ask a company for the facts we're missing, with a person's approval bound to the
// exact text, and see what a reply changes. Sending is off in this workspace, so nothing is e-mailed.
import { ShieldCheck } from "lucide-react";
import { Suspense, useState } from "react";
import { useT } from "../../i18n/messages";
import { useOutreachTarget, type OutreachTarget } from "../../lib/handoff";
import { useWorkspace } from "../../lib/workspace";
import { shellMessages } from "../../shell/messages";
import { PageHeader } from "../../ui/Panel";
import { CompanyPicker, CompanyPickerSkeleton } from "./CompanyPicker";
import { outreachMessages } from "./messages";
import { OutreachDesk, OutreachDeskSkeleton } from "./OutreachDesk";
import "./Outreach.css";

/** Meriva Oy: resolved by the business ID on its own site, so the desk can always draft for it. */
const DEFAULT_COMPANY = "FI:3652359-1";

export function OutreachScreen() {
  const { t } = useT(outreachMessages);
  const shell = useT(shellMessages);
  const { mode } = useWorkspace();
  const target = useOutreachTarget();
  // A draft started from a bridge is about that bridge, in the workspace that showed it. Picking another
  // company starts from that company's best bridge or opportunity.
  const [subject, setSubject] = useState<OutreachTarget>(target ?? { companyId: DEFAULT_COMPANY });
  const [targetMode] = useState(mode);
  const bridgeId = mode === targetMode ? subject.bridgeId : undefined;

  return (
    <div className="page outreach">
      <PageHeader
        title={shell.t("page_outreach")}
        explainer={t("explainer")}
        actions={
          <Suspense fallback={<CompanyPickerSkeleton />}>
            <CompanyPicker
              value={subject.companyId}
              onChange={(companyId) => setSubject({ companyId })}
            />
          </Suspense>
        }
      />
      <p className="outreach-banner callout callout--amber">
        <ShieldCheck size={16} strokeWidth={1.5} aria-hidden="true" />
        <span>
          <strong>{shell.t("sendingOff")}.</strong> {t("bannerBody")}
        </span>
      </p>
      <Suspense fallback={<OutreachDeskSkeleton />}>
        <OutreachDesk companyId={subject.companyId} bridgeId={bridgeId} />
      </Suspense>
    </div>
  );
}
