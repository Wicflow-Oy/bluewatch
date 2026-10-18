// The small pieces a readiness read is built from, shared by the student page and the idea card.
import { CircleCheck, ScanText, TriangleAlert } from "lucide-react";
import type { CriterionResult, Flag, FlagKind, SimilarItem } from "../types";
import { Chip } from "../../../ui/Chip";
import "./read.css";

/** The order a team reads its flags in: what holds the idea first, then what we removed. */
export const STUDENT_FLAG_ORDER: FlagKind[] = [
  "held_instructions",
  "low_effort",
  "contact_details_removed",
  "personal_link_dropped",
  "grant_dependency",
  "form_text_mismatch",
];

/** "Problem: Says who has it ("quote")" -> the rung and the team's own words, rendered apart. */
function splitQuoted(text: string): { lead: string; quote: string | null } {
  const match = /^(.*?) \("(.*)"\)$/s.exec(text);
  return match ? { lead: match[1], quote: match[2] } : { lead: text, quote: null };
}

/**
 * A strength line from the criterion it names. The line embeds the team's own words, so it never matches
 * the translation table; the criterion's label and rung arrive translated, and its quote stays as written.
 */
function strengthParts(
  text: string,
  criteria: CriterionResult[],
): { lead: string; quote: string | null } {
  const criterion = criteria.find((c) =>
    c.quote ? text.includes(c.quote) : text === `${c.label}: ${c.rung_label}`,
  );
  return criterion
    ? { lead: `${criterion.label}: ${criterion.rung_label}`, quote: criterion.quote }
    : splitQuoted(text);
}

/** Which reader produced the read, always shown: the read is complete with or without Claude. */
export function ReaderLine({ note }: { note: string }) {
  return (
    <p className="ih-reader">
      <ScanText size={16} strokeWidth={1.5} aria-hidden="true" />
      <span>{note}</span>
    </p>
  );
}

/**
 * Amber notices in the order a team needs them. The team never sees near_duplicate (a queue flag);
 * A'Pelago's card passes it first.
 */
export function FlagNotices({
  flags,
  order = STUDENT_FLAG_ORDER,
}: {
  flags: Flag[];
  order?: FlagKind[];
}) {
  const shown = order.flatMap((kind) => flags.filter((f) => f.kind === kind));
  if (shown.length === 0) return null;
  return (
    <ul className="ih-flags">
      {shown.map((flag) => (
        <li key={flag.kind} className="callout callout--amber">
          <TriangleAlert size={16} strokeWidth={1.5} aria-hidden="true" />
          <span>{flag.text}</span>
        </li>
      ))}
    </ul>
  );
}

interface StrengthsProps {
  items: string[];
  /** The read's criteria, which give each strength its label and rung in the reader's language. */
  criteria: CriterionResult[];
  empty: string;
}

export function Strengths({ items, criteria, empty }: StrengthsProps) {
  if (items.length === 0) return <p className="ih-empty-line">{empty}</p>;
  return (
    <ul className="ih-strengths">
      {items.map((item) => {
        const { lead, quote } = strengthParts(item, criteria);
        return (
          <li key={item} className="ih-strength">
            <CircleCheck size={16} strokeWidth={1.75} aria-hidden="true" />
            <div>
              <p className="ih-strength__lead">{lead}</p>
              {quote && <q className="ih-quote">{quote}</q>}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/** Public projects that read alike; the team sees why that is good news, A'Pelago just the list. */
export function SimilarList({ items, note }: { items: SimilarItem[]; note?: string }) {
  return (
    <>
      <ul className="ih-similar">
        {items.map((item) => (
          <li key={item.id}>
            <span className="ih-similar__title">{item.title}</span>
            <Chip tone="grey" wrap>
              {item.source}
            </Chip>
          </li>
        ))}
      </ul>
      {note && <p className="ih-caption">{note}</p>}
    </>
  );
}
