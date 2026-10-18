// The idea card A'Pelago opens from the queue (drawer; a full-screen sheet on a phone): the read, the
// ledger, and the next steps, with "Invite via organiser" first for public leads.
import { ExternalLink, FlaskConical, SearchX } from "lucide-react";
import { useState } from "react";
import { useT } from "../../i18n/messages";
import { ofN } from "../../lib/format";
import { Chip } from "../../ui/Chip";
import { Drawer } from "../../ui/Drawer";
import { EmptyState, LoadingRegion, Skeleton, SkeletonLines } from "../../ui/States";
import { TabPanel, Tabs } from "../../ui/Tabs";
import { ReadTab, StepsTab } from "./CardTabs";
import { CloseButton } from "./CloseButton";
import { ideasMessages } from "./messages";
import { OriginChip } from "./read/chips";
import { LedgerColumns } from "./read/Ledger";
import { SampleChip } from "./SampleData";
import type { IdeaQueue, QueueItem } from "./types";

type CardTab = "read" | "ledger" | "steps";

interface IdeaCardDrawerProps {
  itemId: string | undefined;
  queue: IdeaQueue | null;
  /** The queue is invented sample data. */
  sample: boolean;
  today: string;
  onClose: () => void;
}

export function IdeaCardDrawer({ itemId, queue, sample, today, onClose }: IdeaCardDrawerProps) {
  const { t } = useT(ideasMessages);
  // Keep showing the last card while the drawer slides out after the route has closed it.
  const [shownId, setShownId] = useState(itemId);
  if (itemId !== undefined && itemId !== shownId) setShownId(itemId);
  const item = queue?.items.find((i) => i.id === shownId);
  return (
    <Drawer
      open={itemId !== undefined}
      onClose={onClose}
      label={item?.assessment.title ?? t("idea")}
      variant="card"
    >
      <div className="ih-cardview">
        {queue === null ? (
          <CardSkeleton onClose={onClose} />
        ) : item ? (
          <IdeaCard
            key={item.id}
            item={item}
            queue={queue}
            sample={sample}
            today={today}
            onClose={onClose}
          />
        ) : (
          <Missing onClose={onClose} />
        )}
      </div>
    </Drawer>
  );
}

interface IdeaCardProps {
  item: QueueItem;
  queue: IdeaQueue;
  sample: boolean;
  today: string;
  onClose: () => void;
}

function IdeaCard({ item, queue, sample, today, onClose }: IdeaCardProps) {
  const { t } = useT(ideasMessages);
  const [tab, setTab] = useState<CardTab>("read");
  const read = item.assessment;
  return (
    <>
      <header className="ih-cardview__head">
        <div className="ih-cardview__top">
          <span className={`ih-rank ih-rank--lg mono${item.in_top ? " ih-rank--top" : ""}`}>
            {item.rank}
          </span>
          <div className="ih-cardview__name">
            <h2 className="ih-cardview__title t-h2">{read.title}</h2>
            <div className="ih-cardview__meta">
              {sample && <SampleChip />}
              <OriginChip kind={item.origin.kind} />
              <span className="ih-cardview__of mono">
                #{ofN(item.rank, queue.counts.total ?? queue.items.length)}
              </span>
              {item.in_top && (
                <Chip tone="accent" dot>
                  {t("topN", { n: queue.top_n })}
                </Chip>
              )}
            </div>
          </div>
          <CloseButton onClose={onClose} />
        </div>
        {sample && (
          <p className="callout callout--amber">
            <FlaskConical aria-hidden="true" />
            {t("sampleCardNote")}
          </p>
        )}
        <CardSource item={item} />
      </header>
      <div className="ih-cardview__band">
        <Tabs
          idPrefix="ih-card"
          label={t("cardTabs")}
          value={tab}
          onChange={setTab}
          tabs={[
            { id: "read", label: t("tab_read") },
            {
              id: "ledger",
              label: t("tab_ledger"),
              count: Object.values(read.ledger).reduce((n, items) => n + items.length, 0),
            },
            { id: "steps", label: t("tab_steps"), count: read.next_steps.length },
          ]}
        />
        <span className="ih-cardview__stamp mono">{read.rubric_version}</span>
      </div>
      <div className="ih-cardview__body">
        <TabPanel idPrefix="ih-card" tab={tab}>
          {tab === "read" && <ReadTab item={item} today={today} />}
          {tab === "ledger" && <LedgerColumns ledger={read.ledger} />}
          {tab === "steps" && <StepsTab item={item} />}
        </TabPanel>
      </div>
    </>
  );
}

/** Where the idea came from: the team's consent, or a link to the public record. */
function CardSource({ item }: { item: QueueItem }) {
  const { t } = useT(ideasMessages);
  const { origin } = item;
  if (origin.kind === "your_submission") {
    return (
      <div className="ih-cardview__source">
        <p>{t("sharedWithConsent")}</p>
        {origin.facts[0] && <p className="ih-caption">{origin.facts[0]}</p>}
      </div>
    );
  }
  if (!origin.url) return null;
  return (
    <div className="ih-cardview__source ih-cardview__source--row">
      <a className="ih-link" href={origin.url} target="_blank" rel="noopener noreferrer">
        <ExternalLink size={12} strokeWidth={1.5} aria-hidden="true" />
        {t("openSource")}
      </a>
      {origin.checked && <span className="ih-caption mono">{origin.checked}</span>}
    </div>
  );
}

function CardSkeleton({ onClose }: { onClose: () => void }) {
  const { t } = useT(ideasMessages);
  return (
    <LoadingRegion label={t("loadingCard")}>
      <header className="ih-cardview__head">
        <div className="ih-cardview__top">
          <Skeleton width={48} height={48} radius={14} />
          <Skeleton width="60%" height={32} radius={10} />
          <CloseButton onClose={onClose} />
        </div>
        <Skeleton width={200} height={20} />
      </header>
      <div className="ih-cardview__body">
        <SkeletonLines lines={6} gap={12} />
      </div>
    </LoadingRegion>
  );
}

function Missing({ onClose }: { onClose: () => void }) {
  const { t } = useT(ideasMessages);
  return (
    <>
      <header className="ih-cardview__head">
        <div className="ih-cardview__top">
          <span />
          <CloseButton onClose={onClose} />
        </div>
      </header>
      <EmptyState
        icon={<SearchX size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("missingTitle")}
        action={
          <button type="button" className="btn" onClick={onClose}>
            {t("backToQueue")}
          </button>
        }
      >
        {t("missingBody")}
      </EmptyState>
    </>
  );
}
