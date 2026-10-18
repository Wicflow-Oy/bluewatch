// The unknowns this message asks about, drawn as ledger items. When the simulated reply confirms one,
// the same element flips in place (hatch out, teal in), so the change is seen, not just stated.
import { CircleCheck, CircleHelp, MessageSquareText } from "lucide-react";
import type { Evidence, Question } from "../../contracts";
import { useT } from "../../i18n/messages";
import { formatStampDay, humanText, ofN } from "../../lib/format";
import { Chip } from "../../ui/Chip";
import { uiMessages } from "../../ui/messages";
import { Panel } from "../../ui/Panel";
import { Skeleton } from "../../ui/States";
import { gapLabel } from "./labels";
import { outreachMessages } from "./messages";

interface ClosesPanelProps {
  questions: Question[];
  unknowns: Evidence[];
  confirmed: Evidence[];
}

export const closesItemId = (evidenceId: string) => `closes-${evidenceId}`;

export function ClosesPanel({ questions, unknowns, confirmed }: ClosesPanelProps) {
  const { t } = useT(outreachMessages);
  const done = questions.filter((q) => confirmed.some((c) => c.id === q.evidence_id)).length;
  return (
    <Panel
      title={t("closesTitle")}
      meta={
        <span className="mono">{t("confirmedCount", { count: ofN(done, questions.length) })}</span>
      }
    >
      {questions.length === 0 ? (
        <p className="faint">{t("noQuestions")}</p>
      ) : (
        <>
          <ul className="closes">
            {questions.map((q) => (
              <ClosesItem
                key={q.evidence_id}
                question={q}
                unknown={unknowns.find((u) => u.id === q.evidence_id) ?? null}
                fact={confirmed.find((c) => c.id === q.evidence_id) ?? null}
              />
            ))}
          </ul>
          {done > 0 && <p className="closes__note">{t("sessionNote")}</p>}
        </>
      )}
    </Panel>
  );
}

interface ClosesItemProps {
  question: Question;
  unknown: Evidence | null;
  fact: Evidence | null;
}

function ClosesItem({ question, unknown, fact }: ClosesItemProps) {
  const { t } = useT(outreachMessages);
  const ui = useT(uiMessages);
  const field = fact?.field ?? unknown?.field;
  const confirmedAt = fact?.confirmed_by?.at ?? null;
  return (
    <li
      id={closesItemId(question.evidence_id)}
      tabIndex={-1}
      className={`closes__item inset${fact ? " closes__item--confirmed" : ""}`}
    >
      <div className="closes__head">
        <span className="overline">{field ? gapLabel(t, field) : t("openQuestion")}</span>
        {fact ? (
          <Chip tone="teal" icon={<CircleCheck size={12} strokeWidth={2} aria-hidden="true" />}>
            {confirmedAt ? t("confirmedOn", { date: formatStampDay(confirmedAt) }) : t("confirmed")}
          </Chip>
        ) : (
          <Chip tone="hatch" icon={<CircleHelp size={12} strokeWidth={2} aria-hidden="true" />}>
            {ui.t("state_unknown")}
          </Chip>
        )}
      </div>
      {fact ? (
        <p className="closes__claim">{humanText(fact.claim)}</p>
      ) : (
        unknown?.why_unknown && <p className="closes__why">{humanText(unknown.why_unknown)}</p>
      )}
      <p className="closes__ask">
        <MessageSquareText size={14} strokeWidth={1.5} aria-hidden="true" />
        <span>{t(fact ? "asked" : "askCompany", { question: question.text })}</span>
      </p>
    </li>
  );
}

export function ClosesSkeleton() {
  const { t } = useT(outreachMessages);
  return (
    <Panel title={t("closesTitle")}>
      <div className="closes">
        {[0, 1].map((i) => (
          <div key={i} className="closes__item closes__item--loading inset">
            <Skeleton width={96} />
            <Skeleton width="80%" style={{ marginTop: 8 }} />
          </div>
        ))}
      </div>
    </Panel>
  );
}
