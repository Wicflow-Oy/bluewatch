// The draft message for the organisation on the marked rung: a subject and the points it makes. The
// message itself is written in Idea Harbour ("Invite via organiser"), where a person copies and sends it.
import { Sprout } from "lucide-react";
import { Suspense, use } from "react";
import type { ContactPlan } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { usePreset } from "../../lib/preset";
import { href } from "../../lib/router";
import { useWorkspace } from "../../lib/workspace";
import { queuedIdeas, queueItemId } from "./ideaHarbour";
import { scoutMessages } from "./messages";

export function PlanDraft({ plan }: { plan: ContactPlan }) {
  const { t } = useT(scoutMessages);
  const draft = plan.draft;
  if (!draft) return <p className="scout-detail__prose">{t("noDraft")}</p>;
  return (
    <>
      <div className="scout-draft inset">
        <p className="scout-draft__subject">{draft.subject}</p>
        <ul className="scout-draft__points">
          {draft.points.map((point) => (
            <li key={point}>{humanText(point)}</li>
          ))}
        </ul>
      </div>
      <div className="scout-draft__actions">
        <Suspense fallback={null}>
          <IdeaHarbourLink projectId={plan.project_id} />
        </Suspense>
      </div>
      <p className="scout-detail__note">{t("approvalNote")}</p>
    </>
  );
}

/** The team in Idea Harbour's queue when it is there; otherwise the student form the organiser passes on. */
function IdeaHarbourLink({ projectId }: { projectId: string }) {
  const { t } = useT(scoutMessages);
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const ids = use(queuedIdeas(mode, preset));
  const itemId = queueItemId(projectId);
  return ids?.has(itemId) ? (
    <a className="btn btn--primary" href={href({ name: "ideas", itemId })}>
      <Sprout size={14} strokeWidth={1.5} aria-hidden="true" />
      {t("openInIdeaHarbour")}
    </a>
  ) : (
    <a className="btn" href={href({ name: "apply" })}>
      <Sprout size={14} strokeWidth={1.5} aria-hidden="true" />
      {t("studentForm")}
    </a>
  );
}
