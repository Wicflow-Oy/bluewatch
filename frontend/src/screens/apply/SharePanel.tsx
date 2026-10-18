// Consent is a switch that starts off and one button; after sharing, a receipt with the way back (withdraw).
// Sharing is simulated: the idea joins a demo review queue only this browser session sees, and every line
// here says that nothing reaches A'Pelago.
// Wider screens show it as a card in the read; a phone keeps it in the dock at the bottom of the screen.
import { Check, LoaderCircle, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { useT } from "../../i18n/messages";
import { formatClock } from "../../lib/format";
import { Toggle } from "../../ui/Toggle";
import { withSlots } from "../ideas/read/slots";
import type { IdeaAssessment, IdeaSubmission, SessionShares, ShareReceipt } from "../ideas/types";
import { sameSubmission } from "./draft";
import { useMessageText, type Message } from "./message";
import { applyMessages } from "./messages";

export interface Shared {
  receipt: ShareReceipt;
  submission: IdeaSubmission;
}

export type ShareBusy = "share" | "withdraw" | null;

interface SharePanelProps {
  consentText: string;
  read: IdeaAssessment;
  /** What the read was made from: this, not the live form, is what gets shared. */
  readSubmission: IdeaSubmission;
  draftSubmission: IdeaSubmission;
  consent: boolean;
  onConsent: (checked: boolean) => void;
  shared: Shared | null;
  busy: ShareBusy;
  error: Message | null;
  onShare: () => void;
  onWithdraw: () => void;
  /** "card" in the read column; "dock" in the phone's bottom dock. */
  variant: "card" | "dock";
}

export function SharePanel(props: SharePanelProps) {
  const { t } = useT(applyMessages);
  const { shared, readSubmission, draftSubmission, variant } = props;
  const sharedThisRead = shared !== null && sameSubmission(shared.submission, readSubmission);
  const editedSinceShare = sharedThisRead && !sameSubmission(shared.submission, draftSubmission);
  return (
    <div className={`ap-share ap-share--${variant}`}>
      {editedSinceShare && (
        <p className="callout callout--amber">
          <TriangleAlert aria-hidden="true" />
          {t("changedAfterShare")}
        </p>
      )}
      {shared && <Receipt {...props} shared={shared} earlier={!sharedThisRead} />}
      {!sharedThisRead && <Consent {...props} />}
    </div>
  );
}

function Consent({
  consentText,
  read,
  readSubmission,
  draftSubmission,
  consent,
  onConsent,
  busy,
  error,
  onShare,
  variant,
}: SharePanelProps) {
  const { t } = useT(applyMessages);
  const stale = !sameSubmission(readSubmission, draftSubmission);
  const dock = variant === "dock";
  const shareButton = (
    <button
      type="button"
      className="btn btn--primary btn--lg ap-share__button"
      disabled={!consent || busy !== null}
      onClick={onShare}
    >
      {busy === "share" && <Spinner />}
      {t("share")}
    </button>
  );
  const notes = (
    <>
      {stale && (
        <p className="callout callout--amber">
          <TriangleAlert aria-hidden="true" />
          {t("changedAfterRead")}
        </p>
      )}
      {read.tier === "not_yet" && <p className="ap-share__line">{t("notYetNote")}</p>}
      {error && <ShareError message={error} />}
    </>
  );

  if (dock) {
    return (
      <section className="ap-share__consent" data-on={consent} aria-labelledby="ap-share-title">
        <div className="ap-share__row">
          <div className="ap-share__text">
            <h2 className="ap-share__title" id="ap-share-title">
              {t("share")} <SimulatedChip />
            </h2>
            <p className="ap-share__state">{t(consent ? "shareOn" : "shareOff")}</p>
          </div>
          <Toggle size="lg" checked={consent} onChange={onConsent} label={consentText} />
        </div>
        <div className="ap-share__more" inert={!consent}>
          <div>
            <div className="ap-share__in">
              <p className="ap-share__consent-text">{consentText}</p>
              {notes}
              {shareButton}
            </div>
          </div>
        </div>
        {!consent && error && <ShareError message={error} />}
      </section>
    );
  }

  return (
    <section className="ap-share__consent" data-on={consent} aria-labelledby="ap-share-title">
      <h2 className="ap-share__title" id="ap-share-title">
        {t("shareTitle")} <SimulatedChip />
      </h2>
      <p className="ap-share__line">{t("simulatedNote")}</p>
      <Toggle size="lg" checked={consent} onChange={onConsent} label={consentText} />
      {notes}
      <div className="ap-share__actions">{shareButton}</div>
      <p className="ih-caption">{t("consentNote")}</p>
    </section>
  );
}

interface ReceiptProps extends SharePanelProps {
  shared: Shared;
  /** The read on screen is newer than the shared one, which stays in the queue until withdrawn. */
  earlier: boolean;
}

/**
 * Worded from the receipt's fields rather than its message, which the API writes for a demo audience.
 * "demo" means this server keeps shared ideas in memory for the browser session only. Neither kind is
 * delivered to A'Pelago, and the title says so.
 */
function Receipt({ shared, earlier, busy, error, onWithdraw, variant }: ReceiptProps) {
  const { t } = useT(applyMessages);
  const { receipt } = shared;
  const kept = receipt.demo && receipt.expires_at;
  return (
    <ReceiptRow
      id="ap-receipt-title"
      title={t(receipt.demo ? "sharedSession" : "shared")}
      busy={busy}
      error={error}
      onWithdraw={onWithdraw}
    >
      {/* The dock is small: there the title and the removal time stand in for the explanation. */}
      {variant === "card" && <p>{t(receipt.demo ? "simulatedNote" : "sharedBody")}</p>}
      {kept && <KeptUntil iso={kept} />}
      {earlier && <p>{t("earlierVersion")}</p>}
    </ReceiptRow>
  );
}

interface EarlierShareProps {
  shares: SessionShares;
  busy: ShareBusy;
  error: Message | null;
  onWithdraw: () => void;
}

/** An idea this browser session shared before the page was opened again: still shared, still withdrawable. */
export function EarlierShare({ shares, busy, error, onWithdraw }: EarlierShareProps) {
  const { t, tn } = useT(applyMessages);
  return (
    <div className="ap-share ap-share--card">
      <ReceiptRow
        id="ap-earlier-title"
        title={tn("sharedEarlier", shares.count)}
        busy={busy}
        error={error}
        onWithdraw={onWithdraw}
      >
        <p>{t("simulatedNote")}</p>
        {shares.expires_at && <KeptUntil iso={shares.expires_at} />}
      </ReceiptRow>
    </div>
  );
}

interface ReceiptRowProps {
  id: string;
  title: string;
  busy: ShareBusy;
  error: Message | null;
  onWithdraw: () => void;
  children: ReactNode;
}

/** A sea check, what was shared and until when, and Withdraw. */
function ReceiptRow({ id, title, busy, error, onWithdraw, children }: ReceiptRowProps) {
  const { t } = useT(applyMessages);
  return (
    <section className="ap-receipt" aria-labelledby={id}>
      <span className="ap-receipt__ic" aria-hidden="true">
        <Check size={12} strokeWidth={2.5} />
      </span>
      <div className="ap-receipt__text">
        <h2 className="ap-receipt__title" id={id}>
          {title}
        </h2>
        {children}
      </div>
      <button type="button" className="btn btn--sm" disabled={busy !== null} onClick={onWithdraw}>
        {busy === "withdraw" && <Spinner />}
        {t("withdraw")}
      </button>
      {error && <ShareError message={error} />}
    </section>
  );
}

/** The quiet marker that this sharing is a demo: nothing is sent anywhere. */
function SimulatedChip() {
  const { t } = useT(applyMessages);
  return <span className="prototype-pill ap-share__chip">{t("simulated")}</span>;
}

function KeptUntil({ iso }: { iso: string }) {
  const { t } = useT(applyMessages);
  return (
    <p className="ap-receipt__kept">
      {withSlots(t("keptUntil"), { time: <span className="mono">{formatClock(iso)}</span> })}
    </p>
  );
}

function ShareError({ message }: { message: Message }) {
  const say = useMessageText();
  return (
    <p className="callout callout--red" role="alert">
      <TriangleAlert aria-hidden="true" />
      {say(message)}
    </p>
  );
}

export function Spinner() {
  return <LoaderCircle className="ap-spinner" size={16} strokeWidth={2} aria-hidden="true" />;
}
