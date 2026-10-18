// Phones: a floating pill tab bar with the four loop pages and "More", which opens a bottom sheet with the
// other pages, the workspace and preset, the language, the theme and the prototype note.
import { Check, CircleHelp, Ellipsis, X } from "lucide-react";
import { useState } from "react";
import { useLang } from "../i18n/lang";
import { useT } from "../i18n/messages";
import { useMeta } from "../lib/meta";
import { href, pageHref, type PageName } from "../lib/router";
import { Drawer } from "../ui/Drawer";
import { useSlidingIndicator } from "../ui/useSlidingIndicator";
import { LanguageSwitch } from "./LanguageSwitch";
import { shellMessages } from "./messages";
import { NAV, pillLabel } from "./nav";
import { PresetSwitch } from "./PresetSwitch";
import { ThemeToggle } from "./ThemeToggle";
import { WorkspaceChoices } from "./WorkspaceSwitcher";
import "./BottomTabs.css";

const TABS = NAV.filter((n) => n.tab);
const REST = NAV.filter((n) => !n.tab);

function MoreSheet({
  open,
  onClose,
  current,
}: {
  open: boolean;
  onClose: () => void;
  current: PageName | null;
}) {
  const meta = useMeta();
  const { t } = useT(shellMessages);
  return (
    <Drawer open={open} onClose={onClose} label={t("more")} variant="sheet">
      <div className="more">
        <header className="more__header">
          <h2 className="t-h2 more__title">{t("more")}</h2>
          <button type="button" className="icon-btn" onClick={onClose}>
            <X aria-hidden="true" />
            <span className="sr-only">{t("close")}</span>
          </button>
        </header>
        <div className="more__body">
          <ul className="more__list" aria-label={t("pages")}>
            {REST.map((item) => {
              const Icon = item.icon;
              const on = current === item.route;
              return (
                <li key={item.route}>
                  <a
                    className="more__item"
                    href={pageHref(item.route)}
                    aria-current={on ? "page" : undefined}
                    onClick={onClose}
                  >
                    <Icon size={20} strokeWidth={1.5} aria-hidden="true" />
                    <span className="more__label">{pillLabel(item.route, meta.listName)}</span>
                    {on && <Check size={16} strokeWidth={1.75} aria-hidden="true" />}
                  </a>
                </li>
              );
            })}
            <li>
              <a className="more__item" href={href({ name: "guide" })} onClick={onClose}>
                <CircleHelp size={20} strokeWidth={1.5} aria-hidden="true" />
                <span className="more__label">{t("guide")}</span>
              </a>
            </li>
          </ul>
          <WorkspaceChoices />
          <PresetSwitch variant="sheet" />
          <LanguageSwitch variant="sheet" />
          <section className="more__theme">
            <h3 className="overline">{t("theme")}</h3>
            <ThemeToggle variant="labels" />
          </section>
          <p className="more__note">
            <span className="prototype-pill">{t("prototype")}</span> {t("sendingOff")}.
          </p>
        </div>
      </div>
    </Drawer>
  );
}

export function BottomTabs({ current }: { current: PageName | null }) {
  const meta = useMeta();
  const lang = useLang();
  const { t } = useT(shellMessages);
  const [moreOpen, setMoreOpen] = useState(false);
  const inMore = !TABS.some((n) => n.route === current);
  const selected = inMore ? "more" : current;
  const { rootRef, indRef } = useSlidingIndicator<HTMLElement>(selected, lang);

  return (
    <>
      <nav className="tabbar" aria-label={t("mainNav")} ref={rootRef}>
        <span className="tabbar__ind" ref={indRef} aria-hidden="true" />
        {TABS.map((item) => {
          const Icon = item.icon;
          const on = current === item.route;
          return (
            <a
              key={item.route}
              className="tabbar__item"
              href={pageHref(item.route)}
              aria-current={on ? "page" : undefined}
              data-selected={on}
            >
              <Icon strokeWidth={1.5} aria-hidden="true" />
              <span>{pillLabel(item.route, meta.listName)}</span>
            </a>
          );
        })}
        <button
          type="button"
          className="tabbar__item"
          data-selected={inMore}
          aria-haspopup="dialog"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen(true)}
        >
          <Ellipsis strokeWidth={1.5} aria-hidden="true" />
          <span>{t("more")}</span>
        </button>
      </nav>
      <MoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} current={current} />
    </>
  );
}
