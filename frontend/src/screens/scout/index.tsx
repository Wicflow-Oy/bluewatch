// Hackathon scout: founders before they're founders. Winning teams with an idea and proof they can build,
// but no company yet, ranked by a promise score and reached only through organisations.
import { Info, ShieldCheck, Telescope } from "lucide-react";
import { Suspense, use, useDeferredValue } from "react";
import type { Mode } from "../../api";
import type { ContactPlan } from "../../contracts";
import { load, type Loaded } from "../../data";
import { useLang, type Lang } from "../../i18n/lang";
import { useT } from "../../i18n/messages";
import { href } from "../../lib/router";
import { useWorkspace } from "../../lib/workspace";
import { shellMessages } from "../../shell/messages";
import { Chip } from "../../ui/Chip";
import { PageHeader, Panel } from "../../ui/Panel";
import { EmptyState, ErrorState } from "../../ui/States";
import { scoutMessages } from "./messages";
import { isYouthOrSchoolEvent } from "./plan";
import { ScoutBoard } from "./ScoutBoard";
import { ScoutSkeleton } from "./ScoutSkeleton";
import "./Scout.css";

// A failed load shows the scout's own unavailable panel instead of the generic page error.
const plansLoads = new Map<string, Promise<Loaded<ContactPlan[]> | null>>();
function loadPlans(lang: Lang, mode: Mode) {
  const key = `${lang}:${mode}`;
  let loading = plansLoads.get(key);
  if (!loading) {
    loading = load.scout(mode).catch(() => null);
    plansLoads.set(key, loading);
  }
  return loading;
}

export function ScoutScreen() {
  const { t } = useT(scoutMessages);
  const shell = useT(shellMessages);
  return (
    <div className="page scout">
      <PageHeader
        title={shell.t("page_scout")}
        explainer={t("explainer")}
        actions={
          <Chip icon={<ShieldCheck size={12} strokeWidth={1.75} aria-hidden="true" />}>
            {shell.t("sendingOff")}
          </Chip>
        }
      />
      <p className="scout__note">
        <Info size={14} strokeWidth={1.5} aria-hidden="true" />
        {t("scoreNote")}
      </p>
      <Suspense fallback={<ScoutSkeleton />}>
        <ScoutPlans />
      </Suspense>
    </div>
  );
}

function ScoutPlans() {
  const { t } = useT(scoutMessages);
  const shell = useT(shellMessages);
  // The plans' prose comes in the interface language and each workspace offers its own next step. After a
  // switch the current plans stay on screen (with the selection and any open sheet) until the new ones load.
  const lang = useDeferredValue(useLang());
  const mode = useDeferredValue(useWorkspace().mode);
  const loaded = use(loadPlans(lang, mode));
  const icon = <Telescope size={20} strokeWidth={1.5} aria-hidden="true" />;
  if (!loaded) {
    return (
      <Panel className="scout__unavailable">
        <ErrorState
          compact
          icon={icon}
          title={t("unavailableTitle", { page: shell.t("page_scout") })}
        >
          {t("unavailableBody")} {t("otherPagesWork")}
        </ErrorState>
      </Panel>
    );
  }
  const plans = loaded.data.filter((plan) => !isYouthOrSchoolEvent(plan));
  if (plans.length === 0) {
    return (
      <Panel>
        <EmptyState
          compact
          icon={icon}
          title={t("emptyTitle")}
          action={
            <a className="btn" href={href({ name: "founder" })}>
              {t("openFounderView")}
            </a>
          }
        >
          {t("emptyBody")} {t("founderStillChecks")}
        </EmptyState>
      </Panel>
    );
  }
  return <ScoutBoard plans={plans} demoData={loaded.origin === "demo"} />;
}
