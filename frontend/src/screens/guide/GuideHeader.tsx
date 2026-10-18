import { ArrowUpRight } from "lucide-react";
import { useT } from "../../i18n/messages";
import { useIsPhone } from "../../lib/media";
import { href } from "../../lib/router";
import { LanguageSwitch } from "../../shell/LanguageSwitch";
import { shellMessages } from "../../shell/messages";
import { ThemeToggle } from "../../shell/ThemeToggle";
import { AppTile } from "../../ui/Logo";
import { guideMessages } from "./messages";

/** The guide's own bar: its name, the way into the app, the language and the theme. */
export function GuideHeader() {
  const { t } = useT(guideMessages);
  const shell = useT(shellMessages);
  const isPhone = useIsPhone();
  return (
    <header className="guide-header">
      <div className="guide-header__inner">
        <a className="guide-brand" href={href({ name: "guide" })}>
          <AppTile size={28} />
          <span className="guide-brand__name">BlueWatch</span>
          <span className="guide-brand__part">{shell.t("guide")}</span>
        </a>
        <div className="guide-header__end">
          <a
            className="btn btn--ghost btn--sm guide-header__app"
            href={href({ name: "surfacing" })}
          >
            <span>{t("openApp")}</span>
            <ArrowUpRight size={14} strokeWidth={1.75} aria-hidden="true" />
          </a>
          <LanguageSwitch variant={isPhone ? "menu" : "segmented"} />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
