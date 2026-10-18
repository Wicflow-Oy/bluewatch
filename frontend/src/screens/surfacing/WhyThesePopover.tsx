// "Why these": the list's own account of itself in a popover. What the list is, why these rows, the rules
// version, and that it is always on. Why the next company is not on it stays in the list foot, under the rows.
import { Info } from "lucide-react";
import { useCallback, useId, useRef, useState } from "react";
import type { ShortList } from "../../contracts";
import { useT } from "../../i18n/messages";
import { formatStamp } from "../../lib/format";
import { usePreset } from "../../lib/preset";
import { useMeta } from "../../lib/meta";
import { useDismiss } from "../../shell/useDismiss";
import { surfacingMessages } from "./messages";
import { whyTheseText } from "./whyThese";
import "../../shell/Popover.css";

export function WhyThesePopover({ list }: { list: ShortList }) {
  const { t, tn } = useT(surfacingMessages);
  const meta = useMeta();
  const { preset } = usePreset();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const close = useCallback(() => setOpen(false), []);
  useDismiss(rootRef, open, close, triggerRef);

  const n = list.entries.length;
  const empty = Math.max(0, (list.cap ?? n) - n);
  const explainer = t(
    preset === "blue" ? `explainer_${meta.mode}` : `explainer_climate_${meta.mode}`,
  );

  return (
    <div className="why-these" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="btn"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        <Info aria-hidden="true" />
        {t("whyThese")}
      </button>
      {open && (
        <div
          id={panelId}
          className="popover popover--end why-these__panel"
          role="dialog"
          aria-label={t("whyThese")}
        >
          <p className="why-these__lead">{explainer}</p>
          <dl className="why-these__rows">
            <div>
              <dt>{t("whyTheseN", { n })}</dt>
              <dd>{whyTheseText(list.why_these)}</dd>
            </div>
            <div>
              <dt>{t("rules")}</dt>
              <dd className="mono">{list.rules_version}</dd>
            </div>
          </dl>
          <p className="why-these__foot">
            {empty > 0 && `${tn("slotsLeftEmpty", empty)} `}
            {t("alwaysOn")} {t("updatedAt", { stamp: formatStamp(list.generated_at) })}
          </p>
        </div>
      )}
    </div>
  );
}
