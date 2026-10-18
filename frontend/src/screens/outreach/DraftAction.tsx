// The one action a draft's status allows (approve, send, simulate the reply, open the card), with the
// line that says where the draft stands.
import {
  ArrowRight,
  CircleCheck,
  LoaderCircle,
  MailX,
  MessageSquareReply,
  Send,
  ShieldX,
  Stamp,
} from "lucide-react";
import type { ReactNode } from "react";
import type { OutreachDraft } from "../../contracts";
import { useT } from "../../i18n/messages";
import { formatClock, humanText } from "../../lib/format";
import { href } from "../../lib/router";
import { Tooltip } from "../../ui/Tooltip";
import { answeredWords } from "./labels";
import { outreachMessages } from "./messages";
import type { DeskStep, ReadyDesk } from "./useDesk";

export type DraftStatus = NonNullable<OutreachDraft["status"]>;

const shortHash = (hash: string) => `${hash.slice(0, 12)}…`;

interface DraftActionProps {
  desk: ReadyDesk;
  status: DraftStatus;
  onApprove(): void;
  onSend(): void;
  onReply(): void;
}

export function DraftAction({ desk, status, onApprove, onSend, onReply }: DraftActionProps) {
  const text = useT(outreachMessages);
  const { t } = text;
  const { draft, text_hash } = desk.view;
  switch (status) {
    case "pending_approval":
      return (
        <ActionRow
          note={
            <Tooltip content={t("hashTip")}>
              <span className="outreach-hash mono" tabIndex={0}>
                {t("textHash", { hash: shortHash(text_hash) })}
              </span>
            </Tooltip>
          }
          button={
            <StepButton step="approve" busy={desk.busy} onClick={onApprove} icon={Stamp}>
              {t("approve")}
            </StepButton>
          }
        />
      );
    case "approved": {
      const hash = shortHash(draft.approved_text_hash ?? text_hash);
      return (
        <ActionRow
          note={
            <span className="outreach-ok">
              <CircleCheck size={16} strokeWidth={1.5} aria-hidden="true" />
              <span>
                {draft.approved_at
                  ? t("approvedAt", { time: formatClock(draft.approved_at), hash })
                  : t("approvedNoTime", { hash })}
              </span>
            </span>
          }
          button={
            <StepButton step="send" busy={desk.busy} onClick={onSend} icon={Send}>
              {t("send")}
            </StepButton>
          }
        />
      );
    }
    case "blocked_demo":
    case "sent":
      return (
        <ActionRow
          note={
            <span className="outreach-sent">
              <MailX size={16} strokeWidth={1.5} aria-hidden="true" />
              {status === "blocked_demo" ? t("notEmailed") : t("sentToTeam")}
            </span>
          }
          button={
            <StepButton step="reply" busy={desk.busy} onClick={onReply} icon={MessageSquareReply}>
              {t("simulateReply")}
            </StepButton>
          }
        />
      );
    case "replied": {
      const reply = desk.reply;
      return (
        <ActionRow
          note={
            <span className="outreach-ok">
              <CircleCheck size={16} strokeWidth={1.5} aria-hidden="true" />
              <span>
                {reply
                  ? t("replySimulated", {
                      classification: t(`class_${reply.reply.classification}`),
                    })
                  : t("status_replied")}
                {reply?.reply.classification === "answer" && (
                  <span className="outreach-ok__detail">
                    {answeredWords(reply.confirmed.length, draft.questions?.length ?? 0, text)}
                  </span>
                )}
              </span>
            </span>
          }
          button={
            draft.company_id && (
              <a
                className="btn btn--primary btn--lg outreach-action__button"
                href={href({ name: "card", companyId: draft.company_id, tab: "evidence" })}
              >
                {t("openEvidence")}
                <ArrowRight size={16} strokeWidth={1.5} aria-hidden="true" />
              </a>
            )
          }
        />
      );
    }
    default:
      return <ActionRow note={<span className="muted">{t(`status_${status}`)}.</span>} />;
  }
}

function ActionRow({ note, button }: { note: ReactNode; button?: ReactNode }) {
  return (
    <div className="outreach-action__row">
      <div className="outreach-action__note">{note}</div>
      {button}
    </div>
  );
}

interface StepButtonProps {
  step: DeskStep;
  busy: DeskStep | null;
  onClick(): void;
  icon: typeof Send;
  children: ReactNode;
}

function StepButton({ step, busy, onClick, icon: Icon, children }: StepButtonProps) {
  const running = busy === step;
  return (
    <button
      type="button"
      className="btn btn--primary btn--lg outreach-action__button"
      onClick={onClick}
      // aria-disabled, not disabled: a disabled button drops keyboard focus mid-flow.
      aria-disabled={busy !== null}
      aria-busy={running}
    >
      {running ? (
        <LoaderCircle className="outreach-spin" size={16} strokeWidth={2} aria-hidden="true" />
      ) : (
        <Icon size={16} strokeWidth={1.5} aria-hidden="true" />
      )}
      {children}
    </button>
  );
}

/** The sending rules' own reasons, as the desk wrote them. */
export function ReasonList({ reasons }: { reasons: string[] }) {
  return (
    <ul className="outreach-reasons">
      {reasons.map((r) => (
        <li key={r}>{humanText(r)}</li>
      ))}
    </ul>
  );
}

export function PolicyBlock({ reasons }: { reasons: string[] }) {
  const { t } = useT(outreachMessages);
  return (
    <div className="outreach-blocked" role="status">
      <p className="outreach-blocked__title">
        <ShieldX size={16} strokeWidth={1.5} aria-hidden="true" />
        {t("cantGoOut")}
      </p>
      <ReasonList reasons={reasons} />
    </div>
  );
}
