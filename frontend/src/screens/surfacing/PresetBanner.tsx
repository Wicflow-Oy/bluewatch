// Shown while another preset than Blue economy ranks the list: what changed, and the way back.
import { Layers } from "lucide-react";
import { useT } from "../../i18n/messages";
import { presetShort, usePreset } from "../../lib/preset";
import { surfacingMessages } from "./messages";

export function PresetBanner() {
  const { t } = useT(surfacingMessages);
  const { label, options, setPreset } = usePreset();
  const blue = options.find((o) => o.name === "blue")?.label ?? presetShort("blue");
  return (
    <div className="callout callout--accent preset-banner" role="status">
      <Layers aria-hidden="true" />
      <p className="preset-banner__text">
        <strong>{t("presetTitle", { label })}</strong> {t("presetBody", { blue })}
      </p>
      <button type="button" className="btn btn--sm" onClick={() => setPreset("blue")}>
        {t("backTo", { blue })}
      </button>
    </div>
  );
}
