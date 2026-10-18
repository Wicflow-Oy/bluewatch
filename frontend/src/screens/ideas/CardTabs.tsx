// The idea card's Read and Next steps tabs (the Ledger tab is the shared LedgerColumns).
import { useT } from "../../i18n/messages";
import { InvitePanel } from "./InvitePanel";
import { ideasMessages } from "./messages";
import { BandMeters } from "./read/Bands";
import { IdeaTierChip } from "./read/chips";
import { CriteriaList } from "./read/Criteria";
import { readableDates } from "./read/hooks";
import { readMessages } from "./read/messages";
import { FlagNotices, ReaderLine, SimilarList, STUDENT_FLAG_ORDER } from "./read/parts";
import { StepList } from "./read/Steps";
import type { QueueItem } from "./types";

/** A'Pelago sees the near-duplicate flag first: it decides whether this card is worth a read at all. */
const REVIEWER_FLAGS = ["near_duplicate" as const, ...STUDENT_FLAG_ORDER];

export function ReadTab({ item, today }: { item: QueueItem; today: string }) {
  const { t, tn } = useT(ideasMessages);
  const shared = useT(readMessages);
  const read = item.assessment;
  return (
    <div className="ih-cardread">
      <div className="ih-cardread__col">
        <section className="ih-box ih-cardread__tier">
          <IdeaTierChip tier={read.tier} label={read.tier_label} />
          <p className="ih-cardread__rule">{read.tier_rule}</p>
          <ReaderLine note={read.reader_note} />
        </section>
        <BandMeters read={read} />
        <section className="ih-box">
          <h3 className="ih-box__title">{t("col_why")}</h3>
          <ul className="ih-bullets">
            {item.why_here.map((line) => (
              <li key={line}>{readableDates(line, today)}</li>
            ))}
          </ul>
        </section>
        {read.questions.length > 0 && (
          <section className="ih-box">
            <h3 className="ih-box__title">{tn("questions", read.questions.length)}</h3>
            <ol className="ih-numbered">
              {read.questions.map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ol>
          </section>
        )}
      </div>
      <div className="ih-cardread__col">
        <FlagNotices flags={read.flags} order={REVIEWER_FLAGS} />
        <section className="ih-box">
          <h3 className="ih-box__title">
            {shared.t("rubricByCriterion")}
            <small className="mono">{shared.tn("criteriaCount", read.criteria.length)}</small>
          </h3>
          <CriteriaList criteria={read.criteria} />
        </section>
        {read.similar_to.length > 0 && (
          <section className="ih-box">
            <h3 className="ih-box__title">{shared.t("similarProjects")}</h3>
            <SimilarList items={read.similar_to} />
          </section>
        )}
      </div>
    </div>
  );
}

export function StepsTab({ item }: { item: QueueItem }) {
  const { t } = useT(ideasMessages);
  const read = item.assessment;
  const money = item.origin.kind === "your_submission" && (
    <p className="ih-cardsteps__money">{read.funding_note}</p>
  );
  return (
    <div className="ih-cardsteps">
      <section className="ih-box">
        <h3 className="ih-box__title">
          {t("tab_steps")}
          <small className="mono">{read.next_steps.length}</small>
        </h3>
        {read.next_steps.length > 0 ? (
          <StepList steps={read.next_steps} />
        ) : (
          <p className="ih-empty-line">{t("noNextStepYet")}</p>
        )}
      </section>
      {(item.invite || money) && (
        <div className="ih-cardsteps__side">
          {item.invite && <InvitePanel invite={item.invite} />}
          {money}
        </div>
      )}
    </div>
  );
}
