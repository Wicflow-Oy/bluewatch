// The four numbered sections of the student form. Options and limits come from /api/ideas/form.
import type { ReactNode } from "react";
import { useT } from "../../i18n/messages";
import { Panel } from "../../ui/Panel";
import { LoadingRegion, SkeletonLines } from "../../ui/States";
import type {
  Commitment,
  Exists,
  IdeaForm,
  Need,
  PresetName,
  Role,
  TeamCountry,
} from "../ideas/types";
import { asChoices } from "./choices";
import type { Draft, FieldErrors, TextField } from "./draft";
import { ChoiceChips, Field, TextArea } from "./fields";
import { LinkFields } from "./LinkFields";
import { useMessageText } from "./message";
import { applyMessages } from "./messages";
import { TeamRows } from "./TeamRows";

export type DraftUpdate = (update: (draft: Draft) => Draft) => void;

interface AnswerFormProps {
  form: IdeaForm;
  preset: PresetName;
  draft: Draft;
  errors: FieldErrors;
  onChange: DraftUpdate;
}

const NOT_SURE = "not_sure";

const SECTIONS = ["team", "idea", "exists", "needs"] as const;

/** Adds the value to a multi-choice answer, or takes it away when it is already there. */
function toggled<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function AnswerForm({ form, preset, draft, errors, onChange }: AnswerFormProps) {
  const { t } = useT(applyMessages);
  const say = useMessageText();
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    onChange((d) => ({ ...d, [key]: value }));
  const countries = asChoices<TeamCountry>(form.countries);
  const errorText = (key: TextField) => {
    const error = errors[key];
    return error && say(error);
  };

  const text = (key: TextField, label: string, helper: string) => (
    <Field
      label={label}
      helper={helper}
      error={errorText(key)}
      counter={{ length: draft[key].length, limit: form.limits[key] }}
    >
      {({ id, describedBy }) => (
        <TextArea
          id={id}
          describedBy={describedBy}
          value={draft[key]}
          limit={form.limits[key]}
          invalid={Boolean(errors[key])}
          onChange={(value) => set(key, value)}
        />
      )}
    </Field>
  );

  return (
    <div className="ap-sections">
      <Section n={1} title={t("section_team")}>
        <p className="ap-section__note">{t("teamNote")}</p>
        <TeamRows
          rows={draft.team}
          roles={asChoices<Role>(form.roles)}
          maxRows={form.limits.team}
          skillsLimit={form.limits.skills}
          onChange={(team) => set("team", team)}
        />
        <div className="ap-field">
          <span className="ap-field__label">{t("commitment")}</span>
          <ChoiceChips
            label={t("commitment")}
            look="segmented"
            choices={asChoices<Commitment>(form.commitment)}
            selected={draft.commitment ? [draft.commitment] : []}
            onToggle={(value) => set("commitment", draft.commitment === value ? null : value)}
          />
        </div>
        <Field label={t("country")}>
          {({ id }) => (
            <select
              id={id}
              className="input"
              value={draft.country ?? ""}
              onChange={(e) =>
                set("country", countries.find((c) => c.value === e.target.value)?.value ?? null)
              }
            >
              <option value="">{t("choose")}</option>
              {countries.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          )}
        </Field>
      </Section>

      <Section n={2} title={t("section_idea")}>
        <Field
          label={t("title")}
          helper={t("titleHelper")}
          error={errorText("title")}
          counter={{ length: draft.title.length, limit: form.limits.title }}
        >
          {({ id, describedBy }) => (
            <input
              id={id}
              className="input"
              value={draft.title}
              maxLength={form.limits.title}
              required
              aria-describedby={describedBy}
              aria-invalid={Boolean(errors.title) || undefined}
              onChange={(e) => set("title", e.target.value)}
            />
          )}
        </Field>
        {text("problem", t("problem"), t("problemHelper"))}
        {text("who_has_it", t("whoHasIt"), t("whoHasItHelper"))}
        {text("solution", t("solution"), t("solutionHelper"))}
        {text("who_pays", t("whoPays"), t("whoPaysHelper"))}
        <div className="ap-field">
          <span className="ap-field__label">{t("impactArea")}</span>
          <p className="ap-field__helper">{t(`impactHelper_${preset}`)}</p>
          <ChoiceChips
            label={t("impactArea")}
            choices={[...asChoices(form.impact_areas), { value: NOT_SURE, label: t("notSure") }]}
            selected={[draft.impact_area ?? NOT_SURE]}
            onToggle={(value) => set("impact_area", value === NOT_SURE ? null : value)}
          />
        </div>
      </Section>

      <Section n={3} title={t("section_exists")}>
        <ChoiceChips
          label={t("section_exists")}
          choices={asChoices<Exists>(form.exists)}
          selected={draft.exists}
          onToggle={(value) => set("exists", toggled(draft.exists, value))}
        />
        {text("exists_detail", t("existsDetail"), t("existsDetailHelper"))}
      </Section>

      <Section n={4} title={t("section_needs")}>
        <ChoiceChips
          label={t("section_needs")}
          choices={asChoices<Need>(form.needs)}
          selected={draft.needs}
          onToggle={(value) => set("needs", toggled(draft.needs, value))}
        />
        <LinkFields
          links={draft.links}
          max={form.limits.links}
          limit={form.limits.link}
          error={errors.links}
          onChange={(links) => set("links", links)}
        />
      </Section>
    </div>
  );
}

/** The form's shape while /api/ideas/form loads: the four sections with grey lines. */
export function AnswerFormSkeleton() {
  const { t } = useT(applyMessages);
  return (
    <LoadingRegion label={t("loadingForm")}>
      <div className="ap-sections">
        {SECTIONS.map((section, i) => (
          <Section key={section} n={i + 1} title={t(`section_${section}`)}>
            <SkeletonLines lines={3} gap={12} />
          </Section>
        ))}
      </div>
    </LoadingRegion>
  );
}

function Section({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <Panel
      className="ap-section"
      icon={
        <span className="ap-section__num mono" aria-hidden="true">
          {n}
        </span>
      }
      title={title}
    >
      <div className="ap-section__body">{children}</div>
    </Panel>
  );
}
