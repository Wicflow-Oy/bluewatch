import { useEffect, useRef } from "react";
import type { ListEntry } from "../../contracts";
import { useT } from "../../i18n/messages";
import { WORKSPACES } from "../../lib/labels";
import { href, navigate } from "../../lib/router";
import { useWorkspace } from "../../lib/workspace";
import { shellMessages } from "../../shell/messages";
import { useToast } from "../../ui/Toast";

/**
 * After a workspace or preset switch the open company may have left the list: close its card and
 * say so, instead of showing a card for a row that isn't there. A link to a company that was never
 * on the list here (a colleague's link from last week) opens its full card instead.
 */
export function useCloseWhenUnlisted(entries: ListEntry[], companyId: string | undefined) {
  const { t } = useT(shellMessages);
  const { mode } = useWorkspace();
  const toast = useToast();
  // Names from earlier lists, so the message can name a company the current list no longer has.
  const names = useRef(new Map<string, string>());
  const listed = companyId === undefined || entries.some((e) => e.company_id === companyId);

  useEffect(() => {
    if (listed || companyId === undefined) return;
    const company = names.current.get(companyId);
    if (company === undefined) {
      // Replaced, not pushed, so Back does not land on the link and bounce here again.
      window.location.replace(href({ name: "card", companyId }));
      return;
    }
    toast(t("notOnList", { company, name: WORKSPACES[mode].name }));
    navigate({ name: "surfacing" });
  }, [listed, companyId, mode, toast, t]);

  // Runs after the check above, so a switch still sees the names of the list it came from.
  useEffect(() => {
    entries.forEach((e) => names.current.set(e.company_id, e.name));
  }, [entries]);
}
