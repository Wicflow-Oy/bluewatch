// The student page's own header and footer: it stands outside the app shell, as A'Pelago's page.
import { useT } from "../../i18n/messages";
import { href } from "../../lib/router";
import { LanguageSwitch } from "../../shell/LanguageSwitch";
import { shellMessages } from "../../shell/messages";
import { ThemeToggle } from "../../shell/ThemeToggle";
import { AppTile } from "../../ui/Logo";
import { PHONE, useMedia } from "../ideas/read/hooks";
import { applyMessages } from "./messages";

export function ApplyHeader() {
  const { t } = useT(applyMessages);
  const shell = useT(shellMessages);
  const phone = useMedia(PHONE);
  return (
    <header className="ap-header">
      <div className="ap-header__inner">
        <div className="ap-brand">
          <AppTile size={30} />
          <span className="ap-brand__text">
            <span className="ap-brand__name">Idea Harbour</span>
            <span className="ap-brand__by">{t("byApelago")}</span>
          </span>
        </div>
        <div className="ap-header__end">
          <span className="prototype-pill">{shell.t("prototype")}</span>
          <LanguageSwitch variant={phone ? "menu" : "segmented"} />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

export function ApplyFooter() {
  const { t } = useT(applyMessages);
  return (
    <footer className="ap-footer">
      <p>{t("footer")}</p>
      <a className="ap-footer__link" href={href({ name: "guide", track: "idea-harbour" })}>
        {t("howItWorks")}
      </a>
    </footer>
  );
}
