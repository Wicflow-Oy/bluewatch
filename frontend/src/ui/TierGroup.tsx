// One funding tier (certain, likely, possible, unknown, excluded) with every instrument in it, each with
// the rule that decides it. Long groups collapse so a 60-instrument catalogue stays quick to scan.
import { Check, ChevronDown, CircleHelp, X } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import type { Mode } from "../api";
import type { FounderTier, FundingCheck } from "../contracts";
import { useT } from "../i18n/messages";
import { useMeta } from "../lib/meta";
import { TierChip } from "./Chip";
import { Deadline } from "./Deadline";
import { uiMessages } from "./messages";
import { RuleLine, useRuleText } from "./RuleLine";
import { tierMessages } from "./tierMessages";
import "./TierGroup.css";

export type Tier = FounderTier["tier"];

/** Strongest first, the same order the backend ranks tiers in (bluewatch/rules/funding.py). */
export const TIER_ORDER: Tier[] = ["certain", "likely", "possible", "unknown", "excluded"];

/**
 * The tiers grouped by the word a workspace shows for them, strongest first. A'Pelago words certain and
 * likely both "Likely", so they form one group there instead of two groups with the same name.
 */
export function tiersByWord(tierWord: (tier: Tier) => string): Tier[][] {
  const byWord = new Map<string, Tier[]>();
  for (const tier of TIER_ORDER) {
    const word = tierWord(tier);
    byWord.set(word, [...(byWord.get(word) ?? []), tier]);
  }
  return [...byWord.values()];
}

/** Items in one group per tier word (see tiersByWord), strongest first; empty groups are left out. */
export function groupByTierWord<T extends { tier: Tier }>(
  items: T[],
  tierWord: (tier: Tier) => string,
): { tier: Tier; items: T[] }[] {
  return tiersByWord(tierWord)
    .map((tiers) => ({ tier: tiers[0], items: items.filter((item) => tiers.includes(item.tier)) }))
    .filter((group) => group.items.length > 0);
}

/** What a group of tiers means; only certain and likely ever share a word, and the pair has its own sentence. */
export function useTierMeaning(): (tiers: Tier[]) => string {
  const { t } = useT(tierMessages);
  return useCallback(
    (tiers: Tier[]) => (tiers.length > 1 ? t("meaning_certainOrLikely") : t(`meaning_${tiers[0]}`)),
    [t],
  );
}

/** The unknown, unless the deciding rule already says it (the backend often writes "still unknown: …"). */
export function unknownBeyondRule(rule: string, unknownReason?: string | null): string | null {
  return unknownReason && !rule.includes(unknownReason) ? unknownReason : null;
}

export interface TierItem {
  id: string;
  name: string;
  tier: Tier;
  rule: string;
  ruleSource?: string | null;
  ruleVerified: boolean;
  deadline?: string | null;
  upgradePath?: string | null;
  unknownReason?: string | null;
  /** One quiet line under the name, such as the kind and the funder. */
  detail?: string | null;
  deadlineNote?: string | null;
  /** Each hard rule as it was checked: the "Why" behind the tier. */
  checks?: FundingCheck[];
  /** Why this item is pinned to the top of its group ("Decided by registration country"). */
  pinnedLabel?: string | null;
}

interface TierGroupProps {
  /** The group's tier; its items may also hold a tier the workspace words the same (see tiersByWord). */
  tier: Tier;
  mode: Mode;
  items: TierItem[];
  collapsedAfter?: number;
  /** An instrument picked in search: shown highlighted and scrolled into view, never collapsed away. */
  highlightId?: string | null;
}

export function TierGroup({ tier, mode, items, collapsedAfter, highlightId }: TierGroupProps) {
  const { t } = useT(tierMessages);
  const meta = useMeta();
  const meaning = useTierMeaning();
  const limit = collapsedAfter ?? items.length;
  const [expanded, setExpanded] = useState(
    () => items.findIndex((item) => item.id === highlightId) >= limit,
  );
  const hidden = expanded ? 0 : Math.max(0, items.length - limit);
  const shown = hidden > 0 ? items.slice(0, limit) : items;
  const tiers = TIER_ORDER.filter(
    (each) => each === tier || items.some((item) => item.tier === each),
  );
  return (
    <section className="tier-group" aria-label={meta.tier(tier, mode)}>
      <header className="tier-group__header">
        <TierChip tier={tier} mode={mode} />
        <span className="tier-group__count mono">{items.length}</span>
        <p className="tier-group__meaning">{meaning(tiers)}</p>
      </header>
      <ul className="tier-group__items">
        {shown.map((item) => (
          <TierRow key={item.id} item={item} highlighted={item.id === highlightId} />
        ))}
      </ul>
      {items.length > limit && (
        <button
          type="button"
          className="btn btn--ghost btn--sm tier-group__more"
          aria-expanded={expanded}
          onClick={() => setExpanded((open) => !open)}
        >
          <ChevronDown size={14} strokeWidth={1.5} aria-hidden="true" />
          {expanded ? t("showFewer") : t("showMore", { n: hidden })}
        </button>
      )}
    </section>
  );
}

function TierRow({ item, highlighted }: { item: TierItem; highlighted: boolean }) {
  const { t } = useT(uiMessages);
  const { today } = useMeta();
  const ref = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ block: "center" });
  }, [highlighted]);
  // On phones the notes fold into "Why" (see TierGroup.css), so a long group stays scannable.
  const hasNotes = Boolean(unknownBeyondRule(item.rule, item.unknownReason) || item.upgradePath);
  const notes = (
    <TierNotes rule={item.rule} unknownReason={item.unknownReason} upgradePath={item.upgradePath} />
  );
  const modifier = highlighted
    ? " tier-item--highlight"
    : item.pinnedLabel
      ? " tier-item--pinned"
      : "";
  return (
    <li ref={ref} className={`tier-item${modifier}`}>
      {item.pinnedLabel && <p className="overline tier-item__pin">{item.pinnedLabel}</p>}
      <div className="tier-item__head">
        <div className="tier-item__title">
          <h3 className="tier-item__name">{item.name}</h3>
          {item.detail && <p className="tier-item__detail">{item.detail}</p>}
        </div>
        {item.deadline ? (
          <Deadline date={item.deadline} today={today} />
        ) : (
          <span className="tier-item__no-date">{t("noDeadline")}</span>
        )}
      </div>
      <RuleLine rule={item.rule} source={item.ruleSource} verified={item.ruleVerified} />
      {hasNotes && <div className="tier-item__notes">{notes}</div>}
      <WhyDetails
        checks={item.checks ?? []}
        deadlineNote={item.deadlineNote}
        notes={hasNotes ? notes : null}
      />
    </li>
  );
}

interface TierNotesProps {
  rule: string;
  unknownReason?: string | null;
  upgradePath?: string | null;
}

/** What is still unknown beyond the deciding rule, and what would move the company up a tier. */
export function TierNotes({ rule, unknownReason, upgradePath }: TierNotesProps) {
  const { t } = useT(tierMessages);
  const ruleText = useRuleText();
  const unknown = unknownBeyondRule(rule, unknownReason);
  return (
    <>
      {unknown && <TierNote label={t("stillUnknown")} text={ruleText(unknown)} />}
      {upgradePath && <TierNote label={t("toMoveUp")} text={ruleText(upgradePath)} />}
    </>
  );
}

function TierNote({ label, text }: { label: string; text: string }) {
  return (
    <p className="tier-note">
      <span className="tier-note__label">{label}</span> {text}
    </p>
  );
}

function WhyDetails({
  checks,
  deadlineNote,
  notes,
}: {
  checks: FundingCheck[];
  deadlineNote?: string | null;
  /** The tier notes, repeated here for phones only. */
  notes: ReactNode;
}) {
  const { t, tn } = useT(tierMessages);
  const ruleText = useRuleText();
  const notesOnly = checks.length === 0 && !deadlineNote;
  if (notesOnly && !notes) return null;
  return (
    <details className={`tier-item__why${notesOnly ? " tier-item__why--notes-only" : ""}`}>
      <summary>
        <ChevronDown size={14} strokeWidth={1.5} aria-hidden="true" />
        {t("why")}
        {checks.length > 0 && (
          <span className="tier-item__why-count">{tn("rules", checks.length)}</span>
        )}
      </summary>
      {notes && <div className="tier-item__why-notes">{notes}</div>}
      {checks.length > 0 && (
        <ul className="checks">
          {checks.map((check, i) => (
            <CheckRow key={`${check.name}-${i}`} check={check} />
          ))}
        </ul>
      )}
      {deadlineNote && <TierNote label={t("aboutDeadline")} text={ruleText(deadlineNote)} />}
    </details>
  );
}

const OUTCOME_ICON = { pass: Check, fail: X, unknown: CircleHelp } as const;

/** The backend's check names, as message keys; a name not listed here is shown as it arrives. */
const CHECK_NAME = {
  Age: "check_age",
  "Applicant type": "check_applicantType",
  Consortium: "check_consortium",
  Country: "check_country",
  "Other rule": "check_otherRule",
  Size: "check_size",
  Theme: "check_theme",
  TRL: "check_trl",
} as const;

/** Where a rule was read; only "read" and "sedia" (the EU portal) mean the funder's own page. */
const SOURCE_TAG = {
  read: "tag_read",
  sedia: "tag_sedia",
  snippet: "tag_snippet",
  inferred: "tag_inferred",
  unverified: "tag_unverified",
} as const;

function isKeyOf<T extends object>(map: T, key: string): key is Extract<keyof T, string> {
  return Object.hasOwn(map, key);
}

function CheckRow({ check }: { check: FundingCheck }) {
  const { t } = useT(tierMessages);
  const ruleText = useRuleText();
  const Icon = OUTCOME_ICON[check.outcome];
  const name = isKeyOf(CHECK_NAME, check.name) ? t(CHECK_NAME[check.name]) : check.name;
  const source = isKeyOf(SOURCE_TAG, check.source_tag)
    ? t(SOURCE_TAG[check.source_tag])
    : ruleText(check.source_tag);
  return (
    <li className={`check check--${check.outcome}`}>
      <span className="check__outcome">
        <Icon size={14} strokeWidth={1.75} aria-hidden="true" />
        <span className="check__name">{name}</span>
        <span className="check__word">{t(`outcome_${check.outcome}`)}</span>
      </span>
      <span className="check__text">{ruleText(check.text)}</span>
      <span className={`check__source${check.verified ? " check__source--verified" : ""}`}>
        {source}
      </span>
    </li>
  );
}
