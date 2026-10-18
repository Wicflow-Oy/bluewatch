// The ranking preset: Blue economy or Climate and circular economy. Same companies and rules; only
// the verticals, keywords, grants and investor theses change, and every screen re-fetches with it.
//   topbar: a select pill with a popover (no longer in the top bar: the scope pill owns the preset)
//   sheet:  the two options with their descriptions, in the phone's More sheet
//   header: a full-width two-segment control for a page header on phones (hidden from 720 px up,
//           where the scope pill carries the switch)
import { ChevronDown, Layers } from "lucide-react";
import { useCallback, useId, useRef, useState } from "react";
import { useT } from "../i18n/messages";
import { presetAbbr, presetShort, usePreset, type PresetName } from "../lib/preset";
import { Segmented } from "../ui/Segmented";
import { ChoiceList, type Choice } from "./ChoiceList";
import { shellMessages } from "./messages";
import { useDismiss } from "./useDismiss";
import "./Popover.css";
import "./PresetSwitch.css";

function usePresetChoices(): Choice<PresetName>[] {
  const { options } = usePreset();
  return options.map((o) => ({ value: o.name, title: o.label, description: o.description }));
}

function PresetMenu() {
  const { t } = useT(shellMessages);
  const { preset, setPreset } = usePreset();
  const choices = usePresetChoices();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(rootRef, open, close, triggerRef);

  return (
    <div className="preset-menu" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="btn preset-menu__trigger"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Layers size={16} strokeWidth={1.5} aria-hidden="true" />
        <span className="preset-menu__label">{presetShort(preset)}</span>
        <span className="preset-menu__abbr" aria-hidden="true">
          {presetAbbr(preset)}
        </span>
        <ChevronDown size={14} strokeWidth={1.5} aria-hidden="true" />
        <span className="sr-only">{t("changePreset")}</span>
      </button>
      {open && (
        <div
          className="popover popover--start preset-menu__panel"
          role="dialog"
          aria-label={t("preset")}
        >
          <div className="popover__head">
            <p className="popover__title">{t("preset")}</p>
          </div>
          <div className="preset-menu__choices">
            <ChoiceList
              label={t("preset")}
              choices={choices}
              value={preset}
              autoFocus
              onChange={(next) => {
                setPreset(next);
                close();
                triggerRef.current?.focus();
              }}
            />
          </div>
          <p className="popover__foot">{t("presetNote")}</p>
        </div>
      )}
    </div>
  );
}

function PresetSheet() {
  const { t } = useT(shellMessages);
  const { preset, setPreset } = usePreset();
  const choices = usePresetChoices();
  const titleId = useId();
  return (
    <section className="preset-sheet" aria-labelledby={titleId}>
      <h3 className="overline" id={titleId}>
        {t("preset")}
      </h3>
      <ChoiceList label={t("preset")} choices={choices} value={preset} onChange={setPreset} />
      <p className="preset-sheet__note">{t("presetNote")}</p>
    </section>
  );
}

function PresetSegments() {
  const { t } = useT(shellMessages);
  const { preset, setPreset, options } = usePreset();
  return (
    <div className="preset-segments">
      <Segmented<PresetName>
        block
        label={t("preset")}
        value={preset}
        onChange={setPreset}
        options={options.map((o) => ({ value: o.name, label: presetShort(o.name) }))}
      />
    </div>
  );
}

export function PresetSwitch({ variant }: { variant: "topbar" | "sheet" | "header" }) {
  if (variant === "topbar") return <PresetMenu />;
  if (variant === "sheet") return <PresetSheet />;
  return <PresetSegments />;
}
