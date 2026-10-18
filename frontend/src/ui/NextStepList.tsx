// One ordered list of what to do next: programmes, grants, investors, buyers and partners together, each
// with its kind, deadline, who acts and why. The card's own data adds tiers and investor fit when given.
import { useCallback, useState } from "react";
import type { Mode } from "../api";
import type { InvestorMatch, NextStep, VentureCard } from "../contracts";
import { useT } from "../i18n/messages";
import { humanText, levelText } from "../lib/format";
import { stepKindLabel, WORKSPACES } from "../lib/labels";
import { vars } from "../lib/motion";
import { href } from "../lib/router";
import { Chip, TierChip, type Tone } from "./Chip";
import { Deadline } from "./Deadline";
import { KindIcon } from "./KindIcon";
import { uiMessages } from "./messages";
import { nextStepListMessages } from "./NextStepList.messages";
import "./NextStepList.css";

type When = NonNullable<InvestorMatch["when"]>;

const WHEN_TONES: Record<When, Tone> = { now: "teal", later: "accent", not_a_fit: "outline" };
const TIERED_KINDS: ReadonlySet<NextStep["kind"]> = new Set(["grant", "programme", "pilot"]);

/** When to approach an investor: now, later or not at all. */
export function InvestorWhenChip({ when }: { when: When }) {
  const { t } = useT(nextStepListMessages);
  return <Chip tone={WHEN_TONES[when]}>{t(`when_${when}`)}</Chip>;
}

/** The rules title these two steps in their own words; every other title is a name and stays as it is. */
function StepTitle({ step }: { step: NextStep }) {
  const { t } = useT(nextStepListMessages);
  if (step.kind === "confirm_match" || step.kind === "ask_company") return t(`title_${step.kind}`);
  return step.title;
}

/** Two lines of "why", with a toggle only when the text is actually cut off. */
function Why({ text }: { text: string }) {
  const { t } = useT(nextStepListMessages);
  const [open, setOpen] = useState(false);
  const [overflows, setOverflows] = useState(false);
  const measure = useCallback((el: HTMLParagraphElement | null) => {
    if (!el) return;
    const observer = new ResizeObserver(() => setOverflows(el.scrollHeight > el.clientHeight + 1));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return (
    <div className="step__why-wrap">
      <p ref={measure} className={`step__why${open ? " step__why--open" : ""}`}>
        {text}
      </p>
      {(overflows || open) && (
        <button
          type="button"
          className="step__more"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? t("less") : t("more")}
        </button>
      )}
    </div>
  );
}

function investorOf(step: NextStep, card?: VentureCard): InvestorMatch | undefined {
  if (step.kind !== "investor") return undefined;
  return card?.investors?.find((i) => `investor:${i.investor_id}` === step.opportunity_id);
}

function StepTags({ step, card, mode }: { step: NextStep; card?: VentureCard; mode: Mode }) {
  const { t } = useT(nextStepListMessages);
  const opportunity = TIERED_KINDS.has(step.kind)
    ? card?.opportunities?.find((o) => o.id === step.opportunity_id)
    : undefined;
  const investor = investorOf(step, card);
  const audience = step.audience ?? "both";
  return (
    <>
      {opportunity?.tier && <TierChip tier={opportunity.tier} mode={mode} />}
      {investor && <Chip wrap>{humanText(investor.fit_label)}</Chip>}
      {investor?.when && <InvestorWhenChip when={investor.when} />}
      <Chip tone="outline" wrap>
        <span className="sr-only">{t("whoActs")}: </span>
        {t(`audience_${audience}`, { name: WORKSPACES[mode].name })}
      </Chip>
    </>
  );
}

interface StepRowProps {
  step: NextStep;
  index: number;
  first: boolean;
  card?: VentureCard;
  mode: Mode;
  today: string;
  compact: boolean;
}

function StepRow({ step, index, first, card, mode, today, compact }: StepRowProps) {
  const { t } = useT(nextStepListMessages);
  const ui = useT(uiMessages);
  const bridge = card?.bridges?.find((b) => b.id === step.opportunity_id);
  const why = step.why ? levelText(humanText(step.why), mode) : null;
  // An investor's "why" is its fit label, which the fit chip already shows.
  const fit = levelText(humanText(investorOf(step, card)?.fit_label ?? ""), mode);
  const whyRepeatsFit = why !== null && why === fit;
  const action = levelText(humanText(step.action), mode);
  return (
    <li className={`step stagger-in${first ? " step--first" : ""}`} style={vars({ "--i": index })}>
      <span className="step__rank" aria-hidden="true">
        {step.rank}
      </span>
      <div className="step__body">
        <div className="step__top">
          <p className="step__title">
            <span className="sr-only">
              {first ? `${t("nextStep")} · ` : ""}
              {t("stepSpoken", { n: step.rank })}
            </span>
            {bridge ? (
              <a href={href({ name: "bridges", bridgeId: bridge.id })}>
                <StepTitle step={step} />
              </a>
            ) : (
              <StepTitle step={step} />
            )}
          </p>
          <Chip
            tone={step.kind === "investor" ? "accent" : "grey"}
            icon={<KindIcon kind={step.kind} size={12} />}
          >
            {stepKindLabel(step.kind)}
          </Chip>
        </div>
        <p className="step__action" title={action}>
          {action}
        </p>
        {!compact && why && !whyRepeatsFit && <Why text={why} />}
        <div className="step__foot">
          {step.deadline ? (
            <Deadline date={step.deadline} today={today} />
          ) : (
            <span className="deadline deadline--none">{ui.t("noDeadline")}</span>
          )}
          <StepTags step={step} card={card} mode={mode} />
        </div>
      </div>
    </li>
  );
}

interface NextStepListProps {
  steps: NextStep[];
  /** The company's card: adds each step's tier, investor fit and bridge link. */
  card?: VentureCard;
  mode: Mode;
  today: string;
  /** Tighter rows without the "why" line (founder view). */
  compact?: boolean;
  limit?: number;
  /** On the venture card a short list points to its Evidence tab, where closing unknowns unlocks more. */
  evidenceTab?: boolean;
}

export function NextStepList({
  steps,
  card,
  mode,
  today,
  compact = false,
  limit,
  evidenceTab = false,
}: NextStepListProps) {
  const { t } = useT(nextStepListMessages);
  const [showAll, setShowAll] = useState(false);
  if (steps.length === 0) {
    const tooLate = card?.assessment.flags?.includes("too_late");
    return (
      <p className="steps__empty">
        {t(tooLate ? "noneTooLate" : evidenceTab ? "none" : "noneYet")}
      </p>
    );
  }
  const ordered = [...steps].sort((a, b) => a.rank - b.rank);
  const visible = limit && !showAll ? ordered.slice(0, limit) : ordered;
  const hidden = ordered.length - visible.length;
  return (
    <div className={`steps${compact ? " steps--compact" : ""}`}>
      <ol className="steps__list">
        {visible.map((step, i) => (
          <StepRow
            key={`${step.rank}-${step.opportunity_id}`}
            step={step}
            index={i}
            first={i === 0}
            card={card}
            mode={mode}
            today={today}
            compact={compact}
          />
        ))}
      </ol>
      {evidenceTab && ordered.length === 1 && <p className="steps__note">{t("onlyOne")}</p>}
      {hidden > 0 && (
        <button type="button" className="btn btn--ghost btn--sm" onClick={() => setShowAll(true)}>
          {t("showMore", { n: hidden })}
        </button>
      )}
    </div>
  );
}
