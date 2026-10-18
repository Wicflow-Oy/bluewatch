import type { ReactNode } from "react";
import { useT } from "../../i18n/messages";
import { shellMessages } from "../../shell/messages";
import { PageHeader } from "../../ui/Panel";
import { bridgesMessages } from "./messages";

interface BridgesHeaderProps {
  actions?: ReactNode;
  /** The mono line under the title: how many bridges, how many of them sure. */
  meta?: ReactNode;
}

export function BridgesHeader({ actions, meta }: BridgesHeaderProps) {
  const { t } = useT(bridgesMessages);
  const shell = useT(shellMessages);
  return (
    <PageHeader
      title={shell.t("page_bridges")}
      meta={meta}
      explainer={t("explainer")}
      actions={actions}
    />
  );
}
