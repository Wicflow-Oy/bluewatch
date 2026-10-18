import { useT } from "../../i18n/messages";
import { precisionMessages } from "./messages";
import { stageKeys } from "./model";

/** A band in the reader's language: stage words are translated, level bands ("4-6", "7") stay figures. */
export function useBandText(): (value: string) => string {
  const { t } = useT(precisionMessages);
  return (value) => {
    const keys = stageKeys(value);
    if (!keys) return value;
    const [from, to] = keys.map((key) => t(key));
    return to === undefined ? from : t("stageRange", { from, to });
  };
}
