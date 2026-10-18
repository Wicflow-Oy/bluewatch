// The message's language, chosen before approval. Choosing another one asks the desk for a new draft.
import type { DraftLanguage } from "../../api";
import { useT } from "../../i18n/messages";
import { Segmented } from "../../ui/Segmented";
import { outreachMessages } from "./messages";

const LANGUAGES: DraftLanguage[] = ["en", "fi", "sv"];

interface LanguageChoiceProps {
  value: DraftLanguage;
  onChange(language: DraftLanguage): void;
  disabled: boolean;
}

export function LanguageChoice({ value, onChange, disabled }: LanguageChoiceProps) {
  const { t } = useT(outreachMessages);
  return (
    <Segmented
      size="sm"
      label={t("messageLanguage")}
      value={value}
      onChange={onChange}
      options={LANGUAGES.map((code) => ({
        value: code,
        label: t(`language_${code}`),
        // While a new draft is being written, the current choice stays focusable; the others wait.
        disabled: disabled && code !== value,
      }))}
    />
  );
}
