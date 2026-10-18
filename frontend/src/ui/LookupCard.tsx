// One company looked up in its register: the register's answer, how fresh it is, and the venture card the
// API built from it. A sole trader is a person, so nothing about them is shown; a closed company shows its
// register status and nothing to act on.
import {
  ArrowUpRight,
  Building2,
  CircleOff,
  DatabaseZap,
  SearchX,
  TriangleAlert,
  UserRoundX,
} from "lucide-react";
import type { ReactNode } from "react";
import type { LookupResult } from "../api";
import type { VentureCard } from "../contracts";
import { useT } from "../i18n/messages";
import { href } from "../lib/router";
import { Chip } from "./Chip";
import { LiveResult } from "./LookupCard.live";
import { lookupCardMessages } from "./LookupCard.messages";
import { SourceStatusPill } from "./SourceStatusPill";
import "./LookupCard.css";

interface LookupCardProps {
  result: LookupResult;
  /** The card POST /api/lookup/card built; null for a sole trader or an ID the register has no company for. */
  card: VentureCard | null;
}

export function LookupCard({ result, card }: LookupCardProps) {
  if (result.natural_person) return <SoleTrader />;
  if (result.company_id) return <Assessed result={result} card={card} />;
  if (result.closed) return <Closed result={result} />;
  if (!card) return <NoCompany result={result} />;
  return <LiveResult result={result} card={card} provenance={<Provenance result={result} />} />;
}

interface MessageProps {
  icon: ReactNode;
  tone?: "down" | "known";
  title: string;
  label: string;
  children: ReactNode;
  aside?: ReactNode;
}

function Message({ icon, tone, title, label, children, aside }: MessageProps) {
  return (
    <section className="lookup-card lookup-card--message" aria-label={label}>
      <span className={`lookup-card__icon${tone ? ` lookup-card__icon--${tone}` : ""}`}>
        {icon}
      </span>
      <div className="lookup-card__text">
        <p className="lookup-card__title">{title}</p>
        <p className="lookup-card__body">{children}</p>
      </div>
      {aside}
    </section>
  );
}

function SoleTrader() {
  const { t } = useT(lookupCardMessages);
  return (
    <Message
      icon={<UserRoundX size={20} strokeWidth={1.5} aria-hidden="true" />}
      title={t("soleTraderTitle")}
      label={t("resultLabel")}
    >
      {t("soleTraderBody")}
    </Message>
  );
}

/** The register's word for a company that is not trading normally; unknown statuses show as given. */
export function RegisterStatusChip({ status }: { status: string | null }) {
  const label = useRegisterStatus(status);
  return label ? <Chip tone="red">{label}</Chip> : null;
}

const STATUS_KEYS: Record<string, MessageKey> = {
  ceased: "status_ceased",
  deleted: "status_deleted",
  bankrupt: "status_bankrupt",
  "in liquidation": "status_liquidation",
  "winding up": "status_windingUp",
  "in restructuring": "status_restructuring",
};

type MessageKey = keyof typeof lookupCardMessages.en;

function useRegisterStatus(status: string | null): string | null {
  const { t } = useT(lookupCardMessages);
  if (!status || status === "registered") return null;
  const key = STATUS_KEYS[status];
  return key ? t(key) : status;
}

function Closed({ result }: { result: LookupResult }) {
  const { t } = useT(lookupCardMessages);
  const status = useRegisterStatus(result.registry?.status ?? null);
  const name = result.registry?.name ?? result.business_id;
  return (
    <Message
      icon={<CircleOff size={20} strokeWidth={1.5} aria-hidden="true" />}
      tone="down"
      title={t("closedTitle", { name })}
      label={t("resultLabelNamed", { name })}
      aside={
        <div className="lookup-card__actions">
          <Provenance result={result} />
          <RegisterStatusChip status={result.registry?.status ?? null} />
        </div>
      }
    >
      {t("closedBody", { status: status ?? "" })}
    </Message>
  );
}

function NoCompany({ result }: { result: LookupResult }) {
  const { t } = useT(lookupCardMessages);
  if (result.recorded_only)
    return (
      <Message
        icon={<DatabaseZap size={20} strokeWidth={1.5} aria-hidden="true" />}
        title={t("notRecordedTitle")}
        label={t("resultLabel")}
        aside={
          // A setting, not an outage: the register was never asked.
          <Chip tone="grey" dot>
            {t("recordedChip")}
          </Chip>
        }
      >
        {t("notRecordedBody")}
      </Message>
    );
  const { label, detail, state } = result.status;
  const down = state === "unavailable";
  const Icon = down ? TriangleAlert : SearchX;
  return (
    <Message
      icon={<Icon size={20} strokeWidth={1.5} aria-hidden="true" />}
      tone={down ? "down" : undefined}
      title={down ? t("registerDownTitle", { register: label }) : t("notFoundTitle")}
      label={t("resultLabel")}
      aside={<SourceStatusPill status={result.status} />}
    >
      {!down
        ? t("notFoundBody")
        : detail
          ? t("registerDownBody", { detail })
          : t("registerDownNoReason")}
    </Message>
  );
}

function Assessed({ result, card }: LookupCardProps) {
  const { t } = useT(lookupCardMessages);
  const name = card?.company.names[0] ?? result.registry?.name ?? result.business_id;
  return (
    <Message
      icon={<Building2 size={20} strokeWidth={1.5} aria-hidden="true" />}
      tone="known"
      title={t("assessedTitle", { name })}
      label={t("resultLabelNamed", { name })}
      aside={
        <div className="lookup-card__actions">
          <Provenance result={result} />
          {result.company_id && (
            <a
              className="btn btn--primary"
              href={href({ name: "card", companyId: result.company_id })}
            >
              {t("openCard")}
              <ArrowUpRight size={14} strokeWidth={1.5} aria-hidden="true" />
            </a>
          )}
        </div>
      }
    >
      {t("assessedBody")}
    </Message>
  );
}

function Provenance({ result }: { result: LookupResult }) {
  const { t } = useT(lookupCardMessages);
  if (result.company_id)
    return (
      <Chip tone="grey" title={t("assessedChipTitle")}>
        {t("assessedChip")}
      </Chip>
    );
  return result.status.state === "live" ? (
    <Chip tone="teal" dot>
      {t("liveChip")}
    </Chip>
  ) : (
    <Chip tone="grey" dot>
      {t("recordedChip")}
    </Chip>
  );
}
