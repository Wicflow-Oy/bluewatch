import type { ReactNode } from "react";
import type { Mode } from "../api";
import type { Bridge, FounderTier, ListEntry } from "../contracts";
import { useT } from "../i18n/messages";
import { confidenceLabel } from "../lib/labels";
import { useMeta } from "../lib/meta";
import { uiMessages } from "./messages";
import "./Chip.css";

export type Tone =
  "teal" | "blue" | "grey" | "amber" | "red" | "violet" | "accent" | "hatch" | "outline";

interface ChipProps {
  tone?: Tone;
  dot?: boolean;
  icon?: ReactNode;
  children: ReactNode;
  title?: string;
  /** Let long text (API wording) wrap instead of truncating. */
  wrap?: boolean;
}

export function Chip({
  tone = "grey",
  dot = false,
  icon,
  children,
  title,
  wrap = false,
}: ChipProps) {
  return (
    <span className={`chip chip--${tone}${wrap ? " chip--wrap" : ""}`} title={title}>
      {dot && <span className="chip__dot" aria-hidden="true" />}
      {icon}
      {children}
    </span>
  );
}

const GROUP_TONE: Record<ListEntry["group"], Tone> = {
  act_now: "accent",
  dive_deeper: "outline",
  not_yet: "grey",
  not_for_us: "red",
};

export function GroupChip({ group }: { group: ListEntry["group"] }) {
  const meta = useMeta();
  return (
    <Chip tone={GROUP_TONE[group]} dot>
      {meta.group(group)}
    </Chip>
  );
}

/** The list's group marker: solid cobalt for Act now, rings for the rest. */
export function GroupDot({ group, size = 10 }: { group: ListEntry["group"]; size?: number }) {
  return (
    <span
      className={`group-dot group-dot--${group}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    />
  );
}

export function groupTone(group: ListEntry["group"]): Tone {
  return GROUP_TONE[group];
}

type Tier = FounderTier["tier"];

const TIER_TONE: Record<Tier, Tone> = {
  certain: "teal",
  likely: "teal",
  possible: "blue",
  excluded: "red",
  unknown: "hatch",
};

/** Tier words differ per workspace (A'Pelago "Likely", Redstone "Probable"); default: the current one. */
export function TierChip({ tier, mode }: { tier: Tier; mode?: Mode }) {
  const meta = useMeta();
  return <Chip tone={TIER_TONE[tier]}>{meta.tier(tier, mode)}</Chip>;
}

const CONFIDENCE_TONE: Record<Bridge["confidence"], Tone> = {
  verified: "teal",
  probable: "accent",
  possible: "outline",
};

export function ConfidenceChip({ confidence }: { confidence: Bridge["confidence"] }) {
  return (
    <Chip tone={CONFIDENCE_TONE[confidence]} dot>
      {confidenceLabel(confidence)}
    </Chip>
  );
}

/** The two-letter registration country, boxed in mono like a plate. */
/** "FI", "NO"; the register placeholder "XX" (no country on record) reads "Unknown". */
export function CountryCode({ code }: { code: string }) {
  const { t } = useT(uiMessages);
  if (code === "XX") return <span className="country-code">{t("state_unknown")}</span>;
  return (
    <span className="country-code mono" title={code}>
      {code}
    </span>
  );
}

/** A small cobalt marker for rows that are new or changed since the last visit. */
export function ChangeMarker({ change }: { change: string }) {
  const { t } = useT(uiMessages);
  const isNew = /^new/i.test(change);
  return (
    <span className="change-marker" title={change}>
      <span className="change-marker__dot" aria-hidden="true" />
      {isNew ? t("changeNew") : t("changeChanged")}
    </span>
  );
}
