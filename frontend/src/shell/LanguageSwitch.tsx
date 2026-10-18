// The interface language: English, Finnish or Swedish. The whole app re-renders in place, so open
// drawers and half-filled forms survive a switch; the API answers in the new language from then on.
//   segmented: EN / FI / SV as a small pill segmented control (desktop top bar, standalone headers)
//   menu:      a compact "EN" pill with a menu (tablet top bar, standalone headers on phones)
//   sheet:     the three languages by name, full width, in the phone's More sheet
import { Check, ChevronDown, CircleHelp } from "lucide-react";
import { useCallback, useId, useRef, useState, type KeyboardEvent } from "react";
import { load } from "../data";
import { LANGS, setLang, useLang, type Lang } from "../i18n/lang";
import { useT } from "../i18n/messages";
import { href } from "../lib/router";
import { Segmented } from "../ui/Segmented";
import { Tooltip } from "../ui/Tooltip";
import { shellMessages } from "./messages";
import { useDismiss } from "./useDismiss";
import "./Popover.css";
import "./LanguageSwitch.css";

/** Loads the new language's labels before switching, so the shell never falls back to a skeleton. */
export function switchLanguage(next: Lang): void {
  load.meta(next).then(
    () => setLang(next),
    () => setLang(next),
  );
}

function LanguageMenu() {
  const lang = useLang();
  const { t } = useT(shellMessages);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(rootRef, open, close, triggerRef);

  const onMenuKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const at = itemRefs.current.findIndex((el) => el === document.activeElement);
    const next = (at + (e.key === "ArrowDown" ? 1 : -1) + LANGS.length) % LANGS.length;
    itemRefs.current[next]?.focus();
  };

  return (
    <div className="lang-menu" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="btn btn--sm lang-menu__trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="mono" aria-hidden="true">
          {lang.toUpperCase()}
        </span>
        <ChevronDown size={12} strokeWidth={1.75} aria-hidden="true" />
        <span className="sr-only">{t("changeLanguage")}</span>
      </button>
      {open && (
        <div
          className="popover popover--end lang-menu__panel"
          role="menu"
          aria-label={t("language")}
          onKeyDown={onMenuKey}
        >
          {LANGS.map((option, i) => (
            <button
              key={option.code}
              ref={(el) => {
                itemRefs.current[i] = el;
              }}
              type="button"
              role="menuitemradio"
              aria-checked={option.code === lang}
              lang={option.code}
              className="menu-row lang-menu__item"
              autoFocus={option.code === lang}
              onClick={() => {
                switchLanguage(option.code);
                close();
                triggerRef.current?.focus();
              }}
            >
              <span className="menu-row__label">{option.label}</span>
              {option.code === lang && <Check size={16} strokeWidth={1.75} aria-hidden="true" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function LanguageSegments({ full }: { full: boolean }) {
  const lang = useLang();
  const { t } = useT(shellMessages);
  return (
    <Segmented<Lang>
      className="lang-seg"
      label={t("language")}
      value={lang}
      onChange={switchLanguage}
      size={full ? "md" : "sm"}
      block={full}
      options={LANGS.map((option) => ({
        value: option.code,
        label: full ? option.label : option.code.toUpperCase(),
        ariaLabel: full ? undefined : option.label,
        lang: option.code,
      }))}
    />
  );
}

function LanguageSheet() {
  const { t } = useT(shellMessages);
  const titleId = useId();
  return (
    <section className="lang-sheet" aria-labelledby={titleId}>
      <h3 className="overline" id={titleId}>
        {t("language")}
      </h3>
      <LanguageSegments full />
    </section>
  );
}

export function LanguageSwitch({ variant = "menu" }: { variant?: "menu" | "sheet" | "segmented" }) {
  if (variant === "segmented") return <LanguageSegments full={false} />;
  return variant === "menu" ? <LanguageMenu /> : <LanguageSheet />;
}

/** The way to the guide, which explains how BlueWatch works; it opens as a page of its own. An icon pill
 * with a tooltip in the top bar, or a small pill with the word. */
export function GuideLink({ variant = "icon" }: { variant?: "icon" | "button" }) {
  const { t } = useT(shellMessages);
  if (variant === "button") {
    return (
      <a className="btn btn--sm guide-link" href={href({ name: "guide" })}>
        <CircleHelp size={14} strokeWidth={1.5} aria-hidden="true" />
        <span>{t("guide")}</span>
      </a>
    );
  }
  return (
    <Tooltip content={t("guide")} placement="bottom">
      <a className="icon-btn guide-link" href={href({ name: "guide" })} aria-label={t("guide")}>
        <CircleHelp size={16} strokeWidth={1.5} aria-hidden="true" />
      </a>
    </Tooltip>
  );
}
