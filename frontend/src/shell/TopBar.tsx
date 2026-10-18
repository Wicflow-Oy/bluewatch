// The frosted top bar: brand and scope on the left, the page pills in the middle, and search, language,
// theme, guide, alerts and the workspace status on the right. One element with three layouts (CSS grid
// areas): desktop one row, tablet a second row for the pills, phones without pills (the tab bar has them).
import { Search } from "lucide-react";
import type { Ref } from "react";
import { useDemoInUse } from "../data";
import { useT } from "../i18n/messages";
import { useMeta } from "../lib/meta";
import { href, type PageName } from "../lib/router";
import { AppTile, Wordmark } from "../ui/Logo";
import { Kbd } from "../ui/States";
import { Tooltip } from "../ui/Tooltip";
import { AlertsButton } from "./AlertsButton";
import { GuideLink, LanguageSwitch } from "./LanguageSwitch";
import { shellMessages } from "./messages";
import { NavPills } from "./NavPills";
import { StatusMenu } from "./StatusMenu";
import { ThemeToggle } from "./ThemeToggle";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";
import "./TopBar.css";

export const IS_MAC =
  typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.userAgent);

function DemoChip() {
  const { t } = useT(shellMessages);
  const demo = useDemoInUse();
  if (!demo) return null;
  return (
    <Tooltip
      placement="bottom"
      content={
        <>
          <div className="tooltip__title">{t("demoTitle")}</div>
          <p className="muted">{t("demoBody")}</p>
        </>
      }
    >
      <span className="demo-chip" tabIndex={0}>
        <span className="demo-chip__dot" aria-hidden="true" />
        <span className="demo-chip__label">{t("demoData")}</span>
      </span>
    </Tooltip>
  );
}

function SearchButton({ onSearch }: { onSearch: () => void }) {
  const { t } = useT(shellMessages);
  return (
    <button
      type="button"
      className="search-trigger"
      aria-label={t("searchLabel", { keys: IS_MAC ? "Command" : "Control" })}
      onClick={onSearch}
    >
      <Search aria-hidden="true" />
      <span className="search-trigger__text">{t("searchPlaceholder")}</span>
      <span className="search-trigger__keys" aria-hidden="true">
        <Kbd>{IS_MAC ? "⌘" : "Ctrl"}</Kbd>
        <Kbd>K</Kbd>
      </span>
    </button>
  );
}

interface TopBarProps {
  current: PageName | null;
  onSearch: () => void;
  headerRef?: Ref<HTMLElement>;
}

export function TopBar({ current, onSearch, headerRef }: TopBarProps) {
  const meta = useMeta();
  return (
    <header className="topbar" ref={headerRef}>
      <div className="topbar__left">
        <a className="brand" href={href({ name: "surfacing" })} aria-label={meta.productName}>
          <AppTile size={32} />
          <Wordmark name={meta.productName} />
        </a>
        <WorkspaceSwitcher />
        <DemoChip />
      </div>
      <div className="topbar__nav">
        <NavPills current={current} />
      </div>
      <div className="topbar__right">
        <SearchButton onSearch={onSearch} />
        <div className="topbar__lang topbar__lang--seg">
          <LanguageSwitch variant="segmented" />
        </div>
        <div className="topbar__lang topbar__lang--menu">
          <LanguageSwitch variant="menu" />
        </div>
        <div className="topbar__theme">
          <ThemeToggle />
        </div>
        <div className="topbar__guide">
          <GuideLink />
        </div>
        <AlertsButton />
        <StatusMenu />
      </div>
    </header>
  );
}
