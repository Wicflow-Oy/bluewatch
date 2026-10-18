// "Share with A'Pelago". Sharing is off in this workspace: the API call carries no company data at all.
import { CircleCheck, LoaderCircle, Send } from "lucide-react";
import { useId, useRef, useState, type RefObject } from "react";
import type { ShareReceipt } from "../../api";
import { shareWithApelago } from "../../data";
import { useT } from "../../i18n/messages";
import { formatStamp } from "../../lib/format";
import { founderMessages } from "./messages";

type ShareState =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "confirmed"; receipt: ShareReceipt }
  | { kind: "unavailable" };

export function ShareRow() {
  const { t } = useT(founderMessages);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [state, setState] = useState<ShareState>({ kind: "idle" });

  const confirm = async () => {
    if (state.kind === "sending") return;
    setState({ kind: "sending" });
    let receipt: ShareReceipt | null;
    try {
      receipt = await shareWithApelago();
    } catch {
      receipt = null;
    }
    dialogRef.current?.close();
    setState(receipt ? { kind: "confirmed", receipt } : { kind: "unavailable" });
  };

  if (state.kind === "confirmed") return <ShareReceiptNote receipt={state.receipt} />;

  return (
    <div className="founder-share inset">
      <button
        type="button"
        className="btn btn--primary btn--lg"
        onClick={() => dialogRef.current?.showModal()}
      >
        <Send size={16} strokeWidth={1.5} aria-hidden="true" />
        {t("shareButton")}
      </button>
      <span className="founder-share__note">{t("shareOff")}</span>
      {state.kind === "unavailable" && (
        <p className="founder-share__error" role="alert">
          {t("shareUnavailable")}
        </p>
      )}
      <ShareDialog dialogRef={dialogRef} sending={state.kind === "sending"} onConfirm={confirm} />
    </div>
  );
}

function ShareReceiptNote({ receipt }: { receipt: ShareReceipt }) {
  return (
    <div className="founder-share founder-share--confirmed callout callout--sea" role="status">
      <CircleCheck size={16} strokeWidth={1.5} aria-hidden="true" />
      <p>{receipt.message}</p>
      <span className="founder-share__time mono">{formatStamp(receipt.at)}</span>
    </div>
  );
}

interface ShareDialogProps {
  dialogRef: RefObject<HTMLDialogElement | null>;
  sending: boolean;
  onConfirm(): void;
}

function ShareDialog({ dialogRef, sending, onConfirm }: ShareDialogProps) {
  const { t } = useT(founderMessages);
  const titleId = useId();
  const close = () => dialogRef.current?.close();
  return (
    <dialog
      ref={dialogRef}
      className="founder-dialog"
      aria-labelledby={titleId}
      onClick={(e) => e.target === e.currentTarget && e.currentTarget.close()}
    >
      {/* The inner box keeps clicks on the content from counting as clicks on the backdrop. */}
      <div className="founder-dialog__box">
        <h2 id={titleId} className="founder-dialog__title">
          {t("shareTitle")}
        </h2>
        <p className="founder-dialog__body">{t("shareBody")}</p>
        <div className="founder-dialog__actions">
          <button type="button" className="btn btn--ghost" onClick={close}>
            {t("cancel")}
          </button>
          <button type="button" className="btn btn--primary" onClick={onConfirm}>
            {sending && (
              <LoaderCircle className="spin" size={16} strokeWidth={1.5} aria-hidden="true" />
            )}
            {t("share")}
          </button>
        </div>
      </div>
    </dialog>
  );
}
