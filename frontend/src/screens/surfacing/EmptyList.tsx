// No row qualifies: say why, and that the list stays empty rather than padded.
import { useT } from "../../i18n/messages";
import { Mark } from "../../ui/Logo";
import { EmptyState } from "../../ui/States";
import { surfacingMessages } from "./messages";
import { whyTheseText } from "./whyThese";

export function EmptyList({ whyThese }: { whyThese: string }) {
  const { t } = useT(surfacingMessages);
  return (
    <EmptyState icon={<Mark size={24} />} title={t("nothingQualifies")}>
      <p>{whyTheseText(whyThese)}</p>
      <p>{t("neverPadded")}</p>
    </EmptyState>
  );
}
