// The avatar: there is no signed-in user, so it is the workspace badge. It opens the workspace's status:
// when the data was read, every source's state, that sending is off, and which build is deployed.
import { Suspense, use, useCallback, useRef, useState } from "react";
import { load, useDemoInUse } from "../data";
import { useT } from "../i18n/messages";
import { formatStamp } from "../lib/format";
import { WORKSPACES, workspaceKind } from "../lib/labels";
import { useWorkspace } from "../lib/workspace";
import { Boundary } from "../ui/Boundary";
import { Skeleton } from "../ui/States";
import { SourceRows } from "../ui/SourceStatusPill";
import { shellMessages } from "./messages";
import { useDismiss } from "./useDismiss";
import { useSettledScope } from "./useSettledScope";
import "./Popover.css";
import "./StatusMenu.css";

/** "Data as of 18 Oct 2026 06:00" for the current list. */
export function AsOf({ className }: { className?: string }) {
  const { t } = useT(shellMessages);
  const { mode, preset } = useSettledScope();
  const list = use(load.list(mode, preset)).data;
  return (
    <p className={className}>
      {t("dataAsOf")} <span className="mono">{formatStamp(list.generated_at)}</span>
    </p>
  );
}

function Sources() {
  const sources = use(load.sources()).data;
  return <SourceRows sources={sources} />;
}

/** The deployed commit from /api/meta, so anyone can check the site runs the latest code. */
function Build() {
  const { t } = useT(shellMessages);
  const build = use(load.meta()).data.build;
  return build ? <span className="status__build mono">{t("build", { build })}</span> : null;
}

function StatusPanel() {
  const { t } = useT(shellMessages);
  const { mode } = useWorkspace();
  const demo = useDemoInUse();
  const name = WORKSPACES[mode].name;
  return (
    <div
      className="popover popover--end status__panel"
      role="dialog"
      aria-label={t("statusTitle", { name })}
    >
      <div className="status__head">
        <p className="popover__title">{t("statusTitle", { name })}</p>
        <p className="status__kind">{workspaceKind(mode)}</p>
        <Boundary fallback={null}>
          <Suspense fallback={<Skeleton width={180} height={12} />}>
            <AsOf className="status__asof" />
          </Suspense>
        </Boundary>
      </div>
      <div className="status__body">
        <p className="overline">{t("sources")}</p>
        <Boundary fallback={null}>
          <Suspense fallback={<Skeleton height={120} />}>
            <Sources />
          </Suspense>
        </Boundary>
      </div>
      {demo && (
        <div className="status__demo callout callout--amber">
          <span>
            <b>{t("demoTitle")}.</b> {t("demoBody")}
          </span>
        </div>
      )}
      <p className="popover__foot status__foot">
        <span className="prototype-pill">{t("prototype")}</span>
        <span>{t("sendingOff")}</span>
        <Boundary fallback={null}>
          <Suspense fallback={null}>
            <Build />
          </Suspense>
        </Boundary>
      </p>
    </div>
  );
}

export function StatusMenu() {
  const { t } = useT(shellMessages);
  const { mode } = useWorkspace();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(rootRef, open, close, triggerRef);
  const name = WORKSPACES[mode].name;

  return (
    <div className="status" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="status__avatar"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={t("statusLabel", { name })}
        onClick={() => setOpen((v) => !v)}
      >
        <span aria-hidden="true">{WORKSPACES[mode].initial}</span>
        <span className="status__dot" aria-hidden="true" />
      </button>
      {open && <StatusPanel />}
    </div>
  );
}
