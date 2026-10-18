import { X } from "lucide-react";
import { useT } from "../../i18n/messages";
import { shellMessages } from "../../shell/messages";

/** The close button in the idea card's and the rubric's drawer headers. */
export function CloseButton({ onClose }: { onClose: () => void }) {
  const { t } = useT(shellMessages);
  return (
    <button type="button" className="icon-btn ih-close" onClick={onClose}>
      <X size={18} strokeWidth={1.5} aria-hidden="true" />
      <span className="sr-only">{t("close")}</span>
    </button>
  );
}
