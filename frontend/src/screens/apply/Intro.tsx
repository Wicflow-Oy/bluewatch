import { Clock, ShieldCheck, UserX } from "lucide-react";
import { useT } from "../../i18n/messages";
import { applyMessages } from "./messages";

/** The invitation's opening: what the page is for and what it asks of the team. */
export function Intro() {
  const { t } = useT(applyMessages);
  return (
    <div className="ap-intro">
      <p className="overline">{t("invitation")}</p>
      <h1 className="ap-intro__title t-h1">{t("introTitle")}</h1>
      <p className="ap-intro__body">{t("introBody")}</p>
      <ul className="ap-facts">
        <li>
          <Clock size={16} strokeWidth={1.5} aria-hidden="true" />
          {t("factTime")}
        </li>
        <li>
          <UserX size={16} strokeWidth={1.5} aria-hidden="true" />
          {t("factNoNames")}
        </li>
        <li>
          <ShieldCheck size={16} strokeWidth={1.5} aria-hidden="true" />
          {t("factYouDecide")}
        </li>
      </ul>
    </div>
  );
}
