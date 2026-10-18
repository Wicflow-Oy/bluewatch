// One team's plan: why it scores what it scores, what we don't know, the offer, the organisation-level
// route and the draft message. Nothing here contacts anyone.
import type { ReactNode } from "react";
import type { ContactPlan, Evidence } from "../../contracts";
import { useT } from "../../i18n/messages";
import { humanText } from "../../lib/format";
import { ScoreBar } from "../../ui/ScoreBar";
import { scoutMessages } from "./messages";
import { scoreParts } from "./plan";
import { PlanDraft } from "./PlanDraft";
import { PlanHeader } from "./PlanHeader";
import { RouteLadder } from "./RouteLadder";

export function PlanDetail({ plan, titleId }: { plan: ContactPlan; titleId: string }) {
  const { t } = useT(scoutMessages);
  const gaps = plan.gaps ?? [];
  return (
    <article className="scout-detail" aria-labelledby={titleId}>
      <PlanHeader plan={plan} titleId={titleId} />
      <Section title={t("whyScore")}>
        <ScoreBar parts={scoreParts(plan)} max={100} total={plan.promise_score.total} />
      </Section>
      {gaps.length > 0 && (
        <Section title={t("unknownsTitle")}>
          <ul className="scout-gaps">
            {gaps.map((gap) => (
              <Gap key={gap.id} gap={gap} />
            ))}
          </ul>
        </Section>
      )}
      {plan.offer && (
        <Section title={t("offerTitle")}>
          <p className="scout-detail__prose">{humanText(plan.offer)}</p>
        </Section>
      )}
      <Section title={t("routeTitle")}>
        <RouteLadder routes={plan.route_ladder ?? []} draftRank={plan.draft?.to_route_rank} />
      </Section>
      <Section title={t("draftTitle")}>
        <PlanDraft plan={plan} />
      </Section>
    </article>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="scout-detail__section">
      <h3 className="scout-detail__heading overline">{title}</h3>
      {children}
    </section>
  );
}

/** An unknown says what would resolve it: a question for the team, or a check we make ourselves. */
function Gap({ gap }: { gap: Evidence }) {
  const { t } = useT(scoutMessages);
  const check = gap.next_check;
  return (
    <li className="scout-gap">
      <span className="scout-gap__swatch" aria-hidden="true" />
      <span className="scout-gap__text">
        <span className="scout-gap__claim">
          {humanText(gap.claim)}
          <span className="sr-only">{t("srUnknown")}</span>
        </span>
        {check?.question && (
          <span className="scout-gap__ask">{t("ask", { question: check.question })}</span>
        )}
        {!check?.question && check?.how && (
          <span className="scout-gap__ask">{t("weCheck", { how: humanText(check.how) })}</span>
        )}
      </span>
    </li>
  );
}
