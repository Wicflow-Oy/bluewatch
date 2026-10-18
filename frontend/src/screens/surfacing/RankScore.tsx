// Redstone sees the weighted rank score on the rank, with its parts on hover.
import type { ReactNode } from "react";
import { useT } from "../../i18n/messages";
import { trunc } from "../../lib/format";
import { Tooltip } from "../../ui/Tooltip";
import { surfacingMessages } from "./messages";

const PARTS = ["fit", "signal", "group", "evidence", "potential"] as const;
type Part = (typeof PARTS)[number];

function isPart(key: string): key is Part {
  return (PARTS as readonly string[]).includes(key);
}

interface RankScoreProps {
  parts: Record<string, number>;
  total: number;
  /** What carries the tooltip (the rank); the score itself when left out. */
  children?: ReactNode;
}

export function RankScore({ parts, total, children }: RankScoreProps) {
  const { t } = useT(surfacingMessages);
  const score = trunc(total, 3);
  const breakdown = Object.entries(parts)
    .filter(([key]) => key !== "total")
    .map(([key, value]) => `${isPart(key) ? t(`part_${key}`) : key} ${trunc(value, 3)}`)
    .join(" · ");
  return (
    <Tooltip
      content={
        <>
          <div className="tooltip__title">{t("rankScore", { score })}</div>
          <p className="muted mono">{breakdown}</p>
        </>
      }
    >
      <span className="srow__rank-score mono" tabIndex={0}>
        {children ?? score}
        <span className="sr-only">{t("rankScoreSpoken", { parts: breakdown })}</span>
      </span>
    </Tooltip>
  );
}
