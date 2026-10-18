// The team's readiness read, in the order they need it: the verdict on a night card, how strong it is,
// what to do next, and only then how every answer was read.
import { ArrowLeft } from "lucide-react";
import { Suspense, type ReactNode, type Ref } from "react";
import { useT } from "../../i18n/messages";
import { Skeleton, SkeletonLines } from "../../ui/States";
import { ideasMessages } from "../ideas/messages";
import { BandMeters } from "../ideas/read/Bands";
import { CriteriaList } from "../ideas/read/Criteria";
import { LedgerGroups } from "../ideas/read/Ledger";
import { readMessages } from "../ideas/read/messages";
import { FlagNotices, SimilarList, Strengths } from "../ideas/read/parts";
import { StepList } from "../ideas/read/Steps";
import type { IdeaAssessment } from "../ideas/types";
import { applyMessages } from "./messages";

/** The spec allows at most three next steps on the student page. */
const MAX_STEPS = 3;

interface ReadResultProps {
  read: IdeaAssessment;
  /** Phones get the ledger as accordions that start closed; wider screens open it. */
  phone: boolean;
  headingRef: Ref<HTMLHeadingElement>;
  /** Back to the form on a phone, where the read replaces it. */
  onEdit?: () => void;
  share: ReactNode;
}

export function ReadResult({ read, phone, headingRef, onEdit, share }: ReadResultProps) {
  const { t } = useT(applyMessages);
  const shared = useT(readMessages);
  const steps = read.next_steps.slice(0, MAX_STEPS);
  return (
    <div className="ap-result">
      <div className="ap-result__head">
        <div className="ap-result__idea">
          <p className="overline">{t("yourRead")}</p>
          <p className="ap-result__title">{read.title}</p>
        </div>
        {onEdit && (
          <button type="button" className="btn btn--sm" onClick={onEdit}>
            <ArrowLeft aria-hidden="true" />
            {t("editAnswers")}
          </button>
        )}
      </div>

      <FlagNotices flags={read.flags} />
      <Hero read={read} headingRef={headingRef} />

      {read.tier === "ask_two" && read.questions.length > 0 && (
        <Card title={t("twoAnswers")}>
          <ol className="ap-questions">
            {read.questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ol>
        </Card>
      )}

      <BandMeters read={read} />

      <Card title={t("strong")} count={read.strengths.length || undefined}>
        <Strengths items={read.strengths} criteria={read.criteria} empty={t("nothingStrong")} />
      </Card>

      {steps.length > 0 && (
        <Card title={t("nextSteps")} count={steps.length}>
          {/* Deadlines count down from the app's "today" in /api/meta. */}
          <Suspense fallback={<SkeletonLines lines={4} />}>
            <StepList steps={steps} />
          </Suspense>
        </Card>
      )}

      <section className="ap-note">
        <h2 className="ap-note__title">{t("aboutMoney")}</h2>
        <p>{read.funding_note}</p>
      </section>

      {read.similar_to.length > 0 && (
        <Card title={shared.t("similarProjects")} count={read.similar_to.length}>
          <SimilarList items={read.similar_to} note={t("similarNote")} />
        </Card>
      )}

      <Card title={t("howWeRead")}>
        <LedgerGroups key={String(phone)} ledger={read.ledger} open={!phone} />
      </Card>

      <Card
        title={shared.t("rubricByCriterion")}
        meta={shared.tn("criteriaCount", read.criteria.length)}
      >
        <CriteriaList criteria={read.criteria} />
      </Card>

      <footer className="ap-result__foot">
        <p className="mono">
          {read.rubric_version} · {read.id}
        </p>
        <p>{read.reader_note}</p>
      </footer>

      {share}
    </div>
  );
}

/** The verdict on the night card: the tier, its rule, and the idea's stage, impact areas and needs. */
function Hero({ read, headingRef }: { read: IdeaAssessment; headingRef: Ref<HTMLHeadingElement> }) {
  const { t } = useT(applyMessages);
  const shared = useT(readMessages);
  const ideas = useT(ideasMessages);
  return (
    <section className="ap-hero" data-tier={read.tier}>
      <p className="ap-hero__k">{t("readinessRead")}</p>
      <h2 className="ap-hero__tier t-hero" ref={headingRef} tabIndex={-1}>
        {shared.t(`studentTier_${read.tier}`)}
      </h2>
      <p className="ap-hero__rule">{read.tier_rule}</p>
      <ul className="ap-hero__chips">
        {read.stage && <li>{t("stageIs", { stage: read.stage })}</li>}
        {read.impact_areas.map((area) => (
          <li key={area}>{area}</li>
        ))}
        {read.needs.map((need) => (
          <li key={need}>{ideas.t(`need_${need}`)}</li>
        ))}
      </ul>
    </section>
  );
}

interface CardProps {
  title: string;
  /** A small mono figure beside the title. */
  count?: number;
  meta?: string;
  children: ReactNode;
}

/** A white card of the read (mockup .ph-card): title with an optional mono count. */
function Card({ title, count, meta, children }: CardProps) {
  const tail = meta ?? (count !== undefined ? String(count) : null);
  return (
    <section className="ap-card">
      <h2 className="ap-card__title">
        {title}
        {tail && <small className="mono">{tail}</small>}
      </h2>
      <div className="ap-card__body">{children}</div>
    </section>
  );
}

/** Shown in the result column before the first read. */
export function WhatYoullGet() {
  const { t } = useT(applyMessages);
  const shared = useT(readMessages);
  return (
    <section className="ap-card ap-promise">
      <h2 className="ap-card__title">{t("promiseTitle")}</h2>
      <ol className="ap-promise__list">
        <li>{t("promiseStands")}</li>
        <li>{t("promiseLedger")}</li>
        <li>{t("promiseSteps")}</li>
      </ol>
      <p className="ap-promise__axiom">{shared.t("bandsCaption")}</p>
    </section>
  );
}

/** The result's shape while the read runs: the night card, two meters, four lines. */
export function ReadSkeleton() {
  const { t } = useT(applyMessages);
  return (
    <div className="ap-result" role="status" aria-label={t("reading")}>
      <div className="ap-hero ap-hero--skeleton">
        <span className="ap-hero__k">{t("readinessRead")}</span>
        <span className="ap-hero__shimmer" style={{ width: "78%", height: 28 }} />
        <span className="ap-hero__shimmer" style={{ width: "60%", height: 12 }} />
        <span className="ap-hero__shimmer" style={{ width: "40%", height: 12 }} />
      </div>
      <div className="ih-bands__pair">
        <Skeleton height={92} radius={20} />
        <Skeleton height={92} radius={20} />
      </div>
      <section className="ap-card">
        <SkeletonLines lines={4} gap={12} />
      </section>
    </div>
  );
}
