// The evidence request as the desk wrote it, read-only: who it goes to and on what basis, its language,
// the text, the questions it asks, and the one action its status allows.
import { FilePenLine, Info } from "lucide-react";
import type { ReactNode } from "react";
import type { DraftLanguage } from "../../api";
import { useT } from "../../i18n/messages";
import { Chip } from "../../ui/Chip";
import { Panel } from "../../ui/Panel";
import { Skeleton, SkeletonLines } from "../../ui/States";
import { Tooltip } from "../../ui/Tooltip";
import { DraftAction, PolicyBlock, ReasonList, type DraftStatus } from "./DraftAction";
import { DraftBody } from "./DraftBody";
import { gapLabel, languageLabel, routeLabel } from "./labels";
import { LanguageChoice } from "./LanguageChoice";
import { outreachMessages } from "./messages";
import type { ReadyDesk } from "./useDesk";

/** Statuses where the sending rules still decide whether the message may go out. */
const RULES_DECIDE: DraftStatus[] = ["draft", "pending_approval", "approved"];

interface DraftPanelProps {
  desk: ReadyDesk;
  language: DraftLanguage;
  onLanguage(language: DraftLanguage): void;
  fieldOf(evidenceId: string): string | null;
  onShowUnknown(evidenceId: string): void;
  onApprove(): void;
  onSend(): void;
  onReply(): void;
}

export function DraftPanel({
  desk,
  language,
  onLanguage,
  fieldOf,
  onShowUnknown,
  onApprove,
  onSend,
  onReply,
}: DraftPanelProps) {
  const { t } = useT(outreachMessages);
  const { draft, decision } = desk.view;
  const status: DraftStatus = draft.status ?? "draft";
  const rulesDecide = RULES_DECIDE.includes(status);
  const route = draft.lawful_route ?? decision.route;
  const reasons = decision.reasons ?? [];
  const questions = draft.questions ?? [];

  return (
    <Panel
      className="outreach-draft"
      title={t("draftTitle")}
      meta={t(`status_${status}`)}
      actions={<EditButton />}
    >
      <dl className="outreach-fields">
        <Field label={t("field_to")}>
          <Chip>{t(`channel_${draft.channel.kind}`)}</Chip>
          {draft.channel.address ? (
            <span className="mono">{draft.channel.address}</span>
          ) : (
            <span className="faint">{t("noAddress")}</span>
          )}
        </Field>
        <Field label={t("field_route")}>
          <span>{route ? routeLabel(t, route) : t("routeUndecided")}</span>
          {rulesDecide && reasons.length > 0 && (
            <Tooltip content={<ReasonList reasons={reasons} />}>
              <button type="button" className="outreach-info" aria-label={t("whyRoute")}>
                <Info size={14} strokeWidth={1.5} aria-hidden="true" />
              </button>
            </Tooltip>
          )}
        </Field>
        <Field label={t("field_language")}>
          {status === "pending_approval" ? (
            <LanguageChoice value={language} onChange={onLanguage} disabled={desk.busy !== null} />
          ) : (
            <span>
              {draft.language ? languageLabel(t, draft.language) : t("languageNotStated")}
            </span>
          )}
        </Field>
        <Field label={t("field_subject")}>
          <span className="outreach-subject">{draft.subject}</span>
        </Field>
      </dl>

      <DraftBody body={draft.body} />

      {questions.length > 0 && (
        <div className="outreach-questions">
          <p className="overline">{t("questionsTitle")}</p>
          <ol className="outreach-questions__list">
            {questions.map((q, i) => {
              const field = fieldOf(q.evidence_id);
              return (
                <li key={q.evidence_id} className="outreach-question">
                  <span className="outreach-question__n mono">{i + 1}</span>
                  <span className="outreach-question__text">{q.text}</span>
                  {field && (
                    <button
                      type="button"
                      className="outreach-closes-link chip-btn"
                      onClick={() => onShowUnknown(q.evidence_id)}
                    >
                      {t("closesField", { field: gapLabel(t, field) })}
                    </button>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      <div className="outreach-action">
        {rulesDecide && !decision.allowed ? (
          <PolicyBlock reasons={reasons} />
        ) : (
          <DraftAction
            desk={desk}
            status={status}
            onApprove={onApprove}
            onSend={onSend}
            onReply={onReply}
          />
        )}
        {desk.failure && (
          <p className="outreach-action__error" role="alert">
            {t("stepFailed")}
            {desk.failure.detail && <span> {desk.failure.detail}</span>}
          </p>
        )}
      </div>
    </Panel>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="outreach-field">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function EditButton() {
  const { t } = useT(outreachMessages);
  return (
    <Tooltip content={t("editTip")} placement="bottom">
      <button type="button" className="btn btn--sm btn--ghost" aria-disabled="true">
        <FilePenLine size={14} strokeWidth={1.5} aria-hidden="true" />
        {t("edit")}
      </button>
    </Tooltip>
  );
}

export function DraftSkeleton() {
  const { t } = useT(outreachMessages);
  const fields = [t("field_to"), t("field_route"), t("field_language"), t("field_subject")];
  return (
    <Panel className="outreach-draft" title={t("draftTitle")}>
      <dl className="outreach-fields">
        {fields.map((label, i) => (
          <Field key={label} label={label}>
            <Skeleton width={i === fields.length - 1 ? "72%" : 200} />
          </Field>
        ))}
      </dl>
      <div className="outreach-body outreach-body--loading inset">
        <SkeletonLines lines={9} gap={12} />
      </div>
    </Panel>
  );
}
