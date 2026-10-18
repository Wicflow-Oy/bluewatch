import { useEffect, useRef, type ReactNode } from "react";
import { useT } from "../../i18n/messages";
import { CARD_TABS, type CardTab } from "../../lib/router";
import { TabPanel, Tabs } from "../../ui/Tabs";
import { cardMessages } from "./messages";

interface CardFrameProps {
  companyId: string;
  tab: CardTab;
  onTabChange(tab: CardTab): void;
  header: ReactNode;
  /** The sheet's open-full-page and close buttons, beside the header. */
  actions?: ReactNode;
  /** When and under which rules the card was assessed, right of the tabs. */
  stamp?: ReactNode;
  counts?: Partial<Record<CardTab, number>>;
  /** The full page keeps the next steps beside every tab. */
  rail?: ReactNode;
  children: ReactNode;
}

/** Header, tab band and tab body. In the sheet the header scrolls away and the tab band sticks to the top. */
export function CardFrame({
  companyId,
  tab,
  onTabChange,
  header,
  actions,
  stamp,
  counts,
  rail,
  children,
}: CardFrameProps) {
  const { t } = useT(cardMessages);
  const headRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // A new tab starts at its top, with the tabs still in view; the sheet scrolls the frame's parent.
    const head = headRef.current;
    const scroller = head?.parentElement;
    if (head && scroller && scroller.scrollTop > head.offsetHeight) {
      scroller.scrollTop = head.offsetHeight;
    }
  }, [tab]);
  const idPrefix = `card-${companyId.replace(/[^A-Za-z0-9-]/g, "-")}`;
  return (
    <>
      <div className="venture-card__head" ref={headRef}>
        <div className="venture-card__entity">{header}</div>
        {actions}
      </div>
      <div className="venture-card__band">
        <Tabs
          tabs={CARD_TABS.map((id) => ({ id, label: t(`tab_${id}`), count: counts?.[id] }))}
          value={tab}
          onChange={onTabChange}
          label={t("tabsLabel")}
          idPrefix={idPrefix}
        />
        {stamp}
      </div>
      <div className="venture-card__body">
        <div className="venture-card__main">
          <TabPanel idPrefix={idPrefix} tab={tab}>
            {children}
          </TabPanel>
        </div>
        {rail && <aside className="venture-card__rail">{rail}</aside>}
      </div>
    </>
  );
}
