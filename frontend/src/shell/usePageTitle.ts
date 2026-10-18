import { useEffect } from "react";
import { useT } from "../i18n/messages";
import { shellMessages } from "./messages";

/** The browser tab reads "Now Surfacing · BlueWatch", in the interface language. */
export function usePageTitle(page: string, product: string): void {
  const { t } = useT(shellMessages);
  const title = t("pageTitle", { page, product });
  useEffect(() => {
    document.title = title;
  }, [title]);
}
