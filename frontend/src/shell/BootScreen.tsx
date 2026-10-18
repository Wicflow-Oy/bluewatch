import { useT } from "../i18n/messages";
import { AppTile, Wordmark } from "../ui/Logo";
import { shellMessages } from "./messages";
import "./BootScreen.css";

// Standalone pages and the boot wait never have /api/meta yet, so the product names itself.
const PRODUCT = "BlueWatch";

/** The tile while the app (or a standalone page) loads, so a slow phone never sees a blank screen. */
export function BootScreen() {
  const { t } = useT(shellMessages);
  return (
    <div className="boot" role="status" aria-label={t("loadingProduct", { product: PRODUCT })}>
      <AppTile size={56} />
      <Wordmark name={PRODUCT} />
    </div>
  );
}
