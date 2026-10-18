// Under the list: why the next company is not on it, what this preset dropped, and the weekly digest.
import { Mail } from "lucide-react";
import type { ListEntry, ShortList } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { surfacingMessages } from "./messages";

export function ListFoot({ list, dropped }: { list: ShortList; dropped: ListEntry[] }) {
  const { t } = useT(surfacingMessages);
  return (
    <footer className="surfacing__foot">
      {list.why_not_next && <p className="surfacing__foot-lead">{humanText(list.why_not_next)}</p>}
      {dropped.length > 0 && (
        <p>{t("dropped", { names: dropped.map((d) => d.name).join(", ") })}</p>
      )}
      <p className="surfacing__foot-digest">
        <Mail aria-hidden="true" />
        {t("digestText")}
      </p>
    </footer>
  );
}
