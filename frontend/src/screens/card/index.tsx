// The venture card: an honest, sourced evaluation of one company and what to do next, in order. It
// renders in the large card sheet over Surfacing and Companies, and as a full page (#/card/{id}).
import { ArrowLeft, Maximize2, X } from "lucide-react";
import { Suspense, use, type ReactNode } from "react";
import type { VentureCard } from "../../contracts";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { formatStampDay } from "../../lib/format";
import { useMeta } from "../../lib/meta";
import { usePreset } from "../../lib/preset";
import { href, pageHref, type CardTab } from "../../lib/router";
import { useWorkspace } from "../../lib/workspace";
import { shellMessages } from "../../shell/messages";
import { EntityHeader } from "../../ui/EntityHeader";
import { Kbd } from "../../ui/States";
import { Tooltip } from "../../ui/Tooltip";
import { CardFrame } from "./CardFrame";
import {
  CardBoundary,
  HeaderSkeleton,
  NotInSet,
  OverviewSkeleton,
  RailSkeleton,
} from "./CardStates";
import { EvidenceTab } from "./EvidenceTab";
import { cardMessages } from "./messages";
import { NextStepsPanel } from "./NextStepsPanel";
import { OpportunitiesTab, opportunityCount } from "./OpportunitiesTab";
import { OutreachTab } from "./OutreachTab";
import { OverviewTab } from "./OverviewTab";
import "./VentureCard.css";

export interface VentureCardViewProps {
  companyId: string;
  tab: CardTab;
  layout: "drawer" | "page";
  onTabChange(tab: CardTab): void;
  onClose?(): void;
}

function ledgerSize(card: VentureCard): number {
  const { facts, assumptions, unknowns, not_applicable } = card.ledger;
  return [facts, assumptions, unknowns, not_applicable].reduce(
    (n, rows) => n + (rows?.length ?? 0),
    0,
  );
}

/** "Assessed 18 Oct · rules-… · Esc": the day and the rules the card was made under. The rules run on a
 * fixed noon timestamp for the day, so a clock time would be misleading. */
function Stamp({ card, layout }: { card: VentureCard; layout: ContentProps["layout"] }) {
  const { t } = useT(cardMessages);
  const { assessed_at, rules_version } = card.assessment;
  return (
    <p className="venture-card__stamp">
      <span>{t("assessedAt", { day: formatStampDay(assessed_at) })}</span>
      <span aria-hidden="true">·</span>
      <span>{rules_version}</span>
      {layout === "drawer" && (
        <>
          <span aria-hidden="true">·</span>
          <Kbd>Esc</Kbd>
        </>
      )}
    </p>
  );
}

type ContentProps = Omit<VentureCardViewProps, "onClose"> & { actions?: ReactNode };

function CardContent({ companyId, tab, layout, onTabChange, actions }: ContentProps) {
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const meta = useMeta();
  // Both requests start before either is awaited, so they run side by side.
  const cardRequest = load.card(companyId, mode, preset);
  const listRequest = load.list(mode, preset);
  const loaded = use(cardRequest);
  const entries = use(listRequest).data.entries;

  if (!loaded) {
    return (
      <>
        {actions && <div className="venture-card__head venture-card__head--bare">{actions}</div>}
        <div className="venture-card__state">
          <NotInSet />
        </div>
      </>
    );
  }

  const card = loaded.data;
  const body = (() => {
    switch (tab) {
      case "overview":
        return (
          <OverviewTab
            card={card}
            mode={mode}
            withNextSteps={layout === "drawer"}
            onTabChange={onTabChange}
          />
        );
      case "evidence":
        return <EvidenceTab card={card} layout={layout} />;
      case "opportunities":
        return <OpportunitiesTab card={card} mode={mode} today={meta.today} />;
      case "outreach":
        return <OutreachTab card={card} />;
    }
  })();

  return (
    <CardFrame
      companyId={companyId}
      tab={tab}
      onTabChange={onTabChange}
      header={
        <EntityHeader
          company={card.company}
          assessment={card.assessment}
          entry={entries.find((e) => e.company_id === companyId)}
          compact={layout === "drawer"}
          evidence={card.evidence}
        />
      }
      actions={actions}
      stamp={<Stamp card={card} layout={layout} />}
      counts={{
        evidence: ledgerSize(card),
        opportunities: opportunityCount(card),
      }}
      rail={layout === "page" && <NextStepsPanel card={card} mode={mode} today={meta.today} />}
    >
      {body}
    </CardFrame>
  );
}

/** The sheet's own controls: open as a full page, and close. They sit beside the header, in flow. */
function SheetActions({
  companyId,
  tab,
  onClose,
}: Pick<VentureCardViewProps, "companyId" | "tab" | "onClose">) {
  const { t } = useT(cardMessages);
  const shell = useT(shellMessages);
  return (
    <div className="venture-card__actions">
      <Tooltip content={t("openFullPage")} placement="bottom">
        <a
          className="icon-btn"
          href={href({ name: "card", companyId, tab })}
          aria-label={t("openFullPage")}
        >
          <Maximize2 size={16} strokeWidth={1.5} aria-hidden="true" />
        </a>
      </Tooltip>
      {onClose && (
        <button type="button" className="icon-btn" onClick={onClose} aria-label={shell.t("close")}>
          <X size={16} strokeWidth={1.5} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

function BackToCompanies() {
  const shell = useT(shellMessages);
  return (
    <a className="btn btn--ghost btn--sm venture-card__back" href={pageHref("companies")}>
      <ArrowLeft size={14} strokeWidth={1.5} aria-hidden="true" />
      {shell.t("page_companies")}
    </a>
  );
}

export function VentureCardView({ onClose, ...content }: VentureCardViewProps) {
  const { companyId, tab, layout } = content;
  const actions =
    layout === "drawer" ? (
      <SheetActions companyId={companyId} tab={tab} onClose={onClose} />
    ) : undefined;
  return (
    <article className={`venture-card venture-card--${layout}`}>
      {layout === "page" && <BackToCompanies />}
      <div className="venture-card__scroll">
        <CardBoundary key={companyId} actions={actions}>
          <Suspense
            fallback={
              <CardFrame
                companyId={companyId}
                tab={tab}
                onTabChange={content.onTabChange}
                header={<HeaderSkeleton />}
                actions={actions}
                rail={layout === "page" && <RailSkeleton />}
              >
                <OverviewSkeleton />
              </CardFrame>
            }
          >
            <CardContent {...content} actions={actions} />
          </Suspense>
        </CardBoundary>
      </div>
    </article>
  );
}
