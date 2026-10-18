import { FlaskConical, Sparkles, Trophy } from "lucide-react";
import { useT } from "../../../i18n/messages";
import { Chip, type Tone } from "../../../ui/Chip";
import { Tooltip } from "../../../ui/Tooltip";
import type { OriginKind, Tier } from "../types";
import { readMessages } from "./messages";
import "./read.css";

const TIER_TONE: Record<Tier, Tone> = { bring_now: "teal", ask_two: "accent", not_yet: "grey" };

/** The reviewer's tier words from the API: sea for "bring now", cobalt for "ask two", grey for "not yet". */
export function IdeaTierChip({ tier, label }: { tier: Tier; label: string }) {
  return (
    <Chip tone={TIER_TONE[tier]} dot wrap>
      {label}
    </Chip>
  );
}

const ORIGIN_TONE: Record<OriginKind, Tone> = {
  your_submission: "accent",
  hackathon_result: "outline",
  research_project: "grey",
};

const ORIGIN_ICON: Partial<Record<OriginKind, typeof Trophy>> = {
  hackathon_result: Trophy,
  research_project: FlaskConical,
};

export function OriginChip({ kind }: { kind: OriginKind }) {
  const { t } = useT(readMessages);
  const Icon = ORIGIN_ICON[kind];
  return (
    <Chip
      tone={ORIGIN_TONE[kind]}
      wrap
      icon={Icon && <Icon size={12} strokeWidth={1.75} aria-hidden="true" />}
    >
      {t(`origin_${kind}`)}
    </Chip>
  );
}

/**
 * Marks a read where Claude listed quoted claims; the note says when and from what. Inside a link
 * (a phone card) it is plain text, since a link can't hold another focusable control.
 */
export function ClaudeChip({ note, plain = false }: { note: string; plain?: boolean }) {
  const { t } = useT(readMessages);
  const chip = (
    <Chip tone="outline" wrap icon={<Sparkles size={12} strokeWidth={1.75} aria-hidden="true" />}>
      {t("claudeRead")}
      {!plain && <span className="sr-only">: {note}</span>}
    </Chip>
  );
  if (plain) return chip;
  return (
    <Tooltip content={note}>
      <span className="ih-focus-chip" tabIndex={0}>
        {chip}
      </span>
    </Tooltip>
  );
}
