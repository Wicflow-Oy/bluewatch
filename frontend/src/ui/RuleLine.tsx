// The rule that decides a tier, and where it was read. "Read on the official page" is only ever said when
// the backend verified the rule there; anything else says plainly that it was not.
import { ArrowUpRight, BadgeCheck, Gavel } from "lucide-react";
import { useCallback } from "react";
import { useT } from "../i18n/messages";
import { hostOf, humanText } from "../lib/format";
import { tierMessages } from "./tierMessages";
import "./RuleLine.css";

// Funders' thresholds arrive as symbols ("from >= 3 countries", "< 50 employees"); a reader wants words.
// Only a symbol in front of a number or an amount is a threshold.
const THRESHOLD = /(?<![-=<>])(>=|≥|<=|≤|<|>)\s*(?=EUR|€|\d)/g;
const THRESHOLD_WORD = {
  ">=": "atLeast",
  "≥": "atLeast",
  "<=": "atMost",
  "≤": "atMost",
  "<": "under",
  ">": "over",
} as const;

/** Backend rule text as a reader reads it: words for keys and threshold symbols, in the interface language. */
export function useRuleText(): (text: string) => string {
  const { t } = useT(tierMessages);
  return useCallback(
    (text: string) =>
      humanText(text).replace(
        THRESHOLD,
        (_match, symbol: keyof typeof THRESHOLD_WORD, offset: number) => {
          const word = t(THRESHOLD_WORD[symbol]);
          // A check can open with its threshold ("< 50 employees"); the word then starts the sentence.
          return `${offset === 0 ? word[0].toUpperCase() + word.slice(1) : word} `;
        },
      ),
    [t],
  );
}

interface RuleLineProps {
  rule: string;
  /** The page the rule comes from (a URL). */
  source?: string | null;
  verified: boolean;
}

export function RuleLine({ rule, source, verified }: RuleLineProps) {
  const { t } = useT(tierMessages);
  const ruleText = useRuleText();
  const host = hostOf(source);
  return (
    <div className="rule-line">
      <p className="rule-line__rule">
        <Gavel size={14} strokeWidth={1.5} aria-hidden="true" />
        <span>{ruleText(rule)}</span>
      </p>
      <p className={`rule-line__source${verified ? " rule-line__source--verified" : ""}`}>
        {verified && <BadgeCheck size={14} strokeWidth={1.5} aria-hidden="true" />}
        <span>{verified ? t("ruleRead") : t("ruleNotRead")}</span>
        {source && host && (
          <a
            className="rule-line__link mono"
            href={source}
            target="_blank"
            rel="noopener noreferrer"
          >
            {host}
            <ArrowUpRight size={12} strokeWidth={1.75} aria-hidden="true" />
            <span className="sr-only"> {t("opensInNewTab")}</span>
          </a>
        )}
      </p>
    </div>
  );
}
