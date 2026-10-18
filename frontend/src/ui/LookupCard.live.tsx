// A company outside the assessed set, as a live card: the register card at once, then the same card with
// the company's own website read, when this workspace reads websites.
import { Info, LoaderCircle } from "lucide-react";
import { Suspense, use, type ReactNode } from "react";
import type { CardReadResponse, LookupResult, SiteRead } from "../api";
import type { VentureCard } from "../contracts";
import { askOnce, load, readCompanySite, type Outcome } from "../data";
import { useLang } from "../i18n/lang";
import { useT } from "../i18n/messages";
import { hostOf } from "../lib/format";
import { useMeta } from "../lib/meta";
import { usePreset } from "../lib/preset";
import { EntityHeader } from "./EntityHeader";
import { lookupCardMessages } from "./LookupCard.messages";
import { SiteClaims } from "./LookupCard.site";
import { evidenceBand, Meter, potentialBand } from "./Meter";
import { NextStepList } from "./NextStepList";
import { ReadinessPanel } from "./ReadinessPanel";
import { SourceStatusPill } from "./SourceStatusPill";

/** Where the website read stands: still running, finished (any state), or the request itself failed. */
type ReadProgress =
  | { kind: "reading"; host: string | null }
  | { kind: "done"; read: SiteRead }
  | { kind: "limited" }
  | { kind: "failed" };

interface LiveResultProps {
  result: LookupResult;
  card: VentureCard;
  provenance: ReactNode;
}

export function LiveResult({ result, card, provenance }: LiveResultProps) {
  const { t } = useT(lookupCardMessages);
  const meta = use(load.meta());
  const lang = useLang();
  const reads = meta.origin === "live" && meta.data.live_reader;
  return (
    <section
      className="lookup-card"
      aria-label={t("resultLabelNamed", { name: card.company.names[0] })}
    >
      <header className="lookup-card__head">
        {provenance}
        <SourceStatusPill status={result.status} />
      </header>
      {reads ? (
        // Keyed by language: the read's card is in the interface language, so a switch reads again.
        <ReadSite key={lang} result={result} card={card} />
      ) : (
        <LiveCard card={card} progress={{ kind: "done", read: OFF }} />
      )}
    </section>
  );
}

const OFF: SiteRead = {
  state: "off",
  host: null,
  url: null,
  read_at: null,
  found_in_register: false,
  claims: 0,
};

function ReadSite({ result, card }: { result: LookupResult; card: VentureCard }) {
  const { mode } = useMeta();
  const lang = useLang();
  const { preset } = usePreset();
  const { country, business_id } = result;
  // One read per company, workspace, preset and language; the register card stays up while it runs.
  const pending = askOnce(result, `${lang}:${mode}:${preset}`, () =>
    settle(readCompanySite(country, business_id, mode, preset)),
  );
  const reading = { kind: "reading", host: registeredHost(result.registry?.website) } as const;
  return (
    <Suspense fallback={<LiveCard card={card} progress={reading} />}>
      <ReadOutcome pending={pending} card={card} />
    </Suspense>
  );
}

/** The register's website field is a bare host as often as a URL ("www.meyerturku.fi"). */
function registeredHost(website: string | null | undefined): string | null {
  if (!website) return null;
  return hostOf(website.includes("//") ? website : `https://${website}`);
}

type Settled = { kind: "read"; card: VentureCard; read: SiteRead } | { kind: "limited" | "failed" };

async function settle(pending: Promise<Outcome<CardReadResponse>>): Promise<Settled> {
  try {
    const outcome = await pending;
    if (outcome.kind === "rejected") return { kind: "limited" };
    if (outcome.kind === "result" && outcome.data.card && outcome.data.read)
      return { kind: "read", card: outcome.data.card, read: outcome.data.read };
  } catch {
    // An unexpected failure keeps the register card and says the read didn't finish.
  }
  return { kind: "failed" };
}

function ReadOutcome({ pending, card }: { pending: Promise<Settled>; card: VentureCard }) {
  const outcome = use(pending);
  if (outcome.kind === "read")
    return <LiveCard card={outcome.card} progress={{ kind: "done", read: outcome.read }} />;
  return <LiveCard card={card} progress={{ kind: outcome.kind }} />;
}

function LiveCard({ card, progress }: { card: VentureCard; progress: ReadProgress }) {
  const { t } = useT(lookupCardMessages);
  const meta = useMeta();
  const { score, levels } = card.assessment;
  const exact = meta.mode === "redstone";
  const read = progress.kind === "done" && progress.read.state === "read" ? progress.read : null;
  return (
    <div className="lookup-card__card">
      <EntityHeader
        company={card.company}
        assessment={card.assessment}
        evidence={card.evidence}
        compact
      />
      <div className="lookup-card__meters">
        <Meter
          kind="potential"
          label={t("potential")}
          value={score.potential}
          band={potentialBand(score.potential)}
          showValue={exact}
          caption={t("potentialCaption")}
        />
        <Meter
          kind="evidence"
          label={t("evidence")}
          value={score.evidence}
          band={evidenceBand(score.evidence)}
          showValue={exact}
          caption={t("evidenceCaption")}
        />
      </div>
      {read && read.claims > 0 ? (
        <SiteClaims read={read} evidence={card.evidence ?? []} />
      ) : (
        <SiteNote progress={progress} />
      )}
      <ReadinessPanel levels={levels} mode={meta.mode} />
      <div className="lookup-card__steps">
        <h3 className="lookup-card__heading">{t("stepsHeading")}</h3>
        <NextStepList
          steps={card.next_steps ?? []}
          card={card}
          mode={meta.mode}
          today={meta.today}
          compact
          limit={3}
        />
      </div>
    </div>
  );
}

/** Why the card rests on register facts: the read is running, off, or could not add anything. */
function SiteNote({ progress }: { progress: ReadProgress }) {
  const { t } = useT(lookupCardMessages);
  if (progress.kind === "reading")
    return (
      <p className="lookup-card__note lookup-card__note--busy" role="status">
        <LoaderCircle size={14} strokeWidth={1.5} aria-hidden="true" />
        <span>{progress.host ? t("siteReading", { host: progress.host }) : t("siteFinding")}</span>
      </p>
    );
  const host = progress.kind === "done" ? (progress.read.host ?? "") : "";
  return (
    <p className="lookup-card__note">
      <Info size={14} strokeWidth={1.5} aria-hidden="true" />
      <span>
        <strong>{t("registerOnly")}</strong> {t(siteMessageKey(progress), { host })}{" "}
        {t("unknownsRule")}
      </span>
    </p>
  );
}

type MessageKey = keyof typeof lookupCardMessages.en;

function siteMessageKey(progress: Exclude<ReadProgress, { kind: "reading" }>): MessageKey {
  if (progress.kind !== "done") return progress.kind === "limited" ? "siteLimited" : "siteFailed";
  const keys: Record<SiteRead["state"], MessageKey> = {
    read: "siteNoClaims",
    no_site: "siteNone",
    unreachable: "siteUnreachable",
    timeout: "siteTimeout",
    budget: "siteBudget",
    failed: "siteFailed",
    off: "siteOff",
  };
  return keys[progress.read.state];
}
