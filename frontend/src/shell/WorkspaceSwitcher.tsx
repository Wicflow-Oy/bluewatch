// The scope pill: the workspace (the mode switch, A'Pelago or Redstone) and the ranking preset, in one
// popover. Switching workspace keeps the page, and keeps an open company when the other workspace lists it
// too. The workspace colour appears only as a dot.
import { ChevronDown } from "lucide-react";
import { useCallback, useId, useRef, useState } from "react";
import type { Mode } from "../api";
import { load } from "../data";
import { useT } from "../i18n/messages";
import { WORKSPACES, workspaceKind } from "../lib/labels";
import { presetAbbr, usePreset, type PresetName } from "../lib/preset";
import { navigate, parseHash } from "../lib/router";
import { useWorkspace } from "../lib/workspace";
import { useToast } from "../ui/Toast";
import { ChoiceList } from "./ChoiceList";
import { shellMessages } from "./messages";
import { useDismiss } from "./useDismiss";
import "./Popover.css";
import "./WorkspaceSwitcher.css";

const MODES: Mode[] = ["apelago", "redstone"];

/** The workspace's colour as a dot (no letter): the scope pill, the avatar and the workspace choices. */
export function WorkspaceMark({ mode, size = 20 }: { mode: Mode; size?: number }) {
  const d = Math.round(size / 2);
  return (
    <span className={`ws-dot ws-dot--${mode}`} style={{ width: d, height: d }} aria-hidden="true" />
  );
}

/** The company open in the Surfacing drawer, if the next workspace doesn't list it: its name. */
async function droppedSelection(
  next: Mode,
  current: Mode,
  preset: PresetName,
): Promise<string | null> {
  const route = parseHash(window.location.hash);
  if (route.name !== "surfacing" || !route.companyId) return null;
  const id = route.companyId;
  const [now, then] = await Promise.all([load.list(current, preset), load.list(next, preset)]);
  if (then.data.entries.some((e) => e.company_id === id)) return null;
  return now.data.entries.find((e) => e.company_id === id)?.name ?? id;
}

export function useSwitchWorkspace(): (next: Mode) => void {
  const { mode, setMode } = useWorkspace();
  const { preset } = usePreset();
  const toast = useToast();
  const { t } = useT(shellMessages);
  return useCallback(
    (next: Mode) => {
      if (next === mode) return;
      const name = WORKSPACES[next].name;
      droppedSelection(next, mode, preset)
        .catch(() => null)
        .then((dropped) => {
          setMode(next);
          if (dropped === null) {
            toast(t("switchedTo", { name }));
            return;
          }
          navigate({ name: "surfacing" });
          toast(t("notOnList", { company: dropped, name }));
        });
    },
    [mode, preset, setMode, toast, t],
  );
}

/** Both workspaces as a choice list, for the phone's More sheet. */
export function WorkspaceChoices() {
  const { mode } = useWorkspace();
  const switchTo = useSwitchWorkspace();
  const { t } = useT(shellMessages);
  const titleId = useId();
  return (
    <section className="ws-choices" aria-labelledby={titleId}>
      <h3 className="overline" id={titleId}>
        {t("workspace")}
      </h3>
      <ChoiceList
        label={t("workspace")}
        value={mode}
        onChange={switchTo}
        choices={workspaceChoices()}
      />
    </section>
  );
}

function workspaceChoices() {
  return MODES.map((m) => ({
    value: m,
    title: WORKSPACES[m].name,
    description: workspaceKind(m),
    leading: <WorkspaceMark mode={m} size={20} />,
  }));
}

/** The scope pill: workspace dot and name, then the preset's short name; opens both choices. */
export function WorkspaceSwitcher() {
  const { mode } = useWorkspace();
  const { preset, setPreset, options } = usePreset();
  const { t } = useT(shellMessages);
  const switchTo = useSwitchWorkspace();
  const workspaces = workspaceChoices();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(rootRef, open, close, triggerRef);
  const done = () => {
    close();
    triggerRef.current?.focus();
  };

  return (
    <div className="scope" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="scope__pill"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <WorkspaceMark mode={mode} size={16} />
        <span className="scope__name">{WORKSPACES[mode].name}</span>
        <span className="sep-dot scope__sep" aria-hidden="true" />
        <span className="scope__preset">{presetAbbr(preset)}</span>
        <ChevronDown size={14} strokeWidth={1.75} className="scope__chevron" aria-hidden="true" />
        <span className="sr-only">{t("scopeLabel")}</span>
      </button>
      {open && (
        <div
          className="popover popover--start scope__panel"
          role="dialog"
          aria-label={t("scopeLabel")}
        >
          <div className="scope__section">
            <p className="overline scope__heading">{t("workspace")}</p>
            <ChoiceList
              label={t("workspace")}
              value={mode}
              autoFocus
              choices={workspaces}
              onChange={(m) => {
                switchTo(m);
                done();
              }}
            />
          </div>
          <div className="scope__section">
            <p className="overline scope__heading">{t("preset")}</p>
            <ChoiceList
              label={t("preset")}
              value={preset}
              choices={options.map((o) => ({
                value: o.name,
                title: o.label,
                description: o.description,
              }))}
              onChange={(next) => {
                setPreset(next);
                done();
              }}
            />
          </div>
          <p className="popover__foot">
            {t("presetNote")} {t("workspaceNote")}
          </p>
        </div>
      )}
    </div>
  );
}
