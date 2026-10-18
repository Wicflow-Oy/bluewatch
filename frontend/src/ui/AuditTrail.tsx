// An append-only log on a vertical rail, oldest first, with the newest line kept in view as it is
// added. The caller words each entry; this component only lays them out.
import { useEffect, useRef } from "react";
import { formatClock } from "../lib/format";
import "./AuditTrail.css";

export type AuditTone = "you" | "company" | "system" | "warning";

export interface AuditEntry {
  /** When it happened (ISO); shown as a Helsinki clock with seconds, so steps seconds apart read in order. */
  at: string;
  action: string;
  actor: string;
  detail: string | null;
  tone: AuditTone;
}

interface AuditTrailProps {
  entries: AuditEntry[];
  /** The list's accessible name. */
  label: string;
  /** What shows before the first entry. */
  empty: string;
}

export function AuditTrail({ entries, label, empty }: AuditTrailProps) {
  const listRef = useRef<HTMLOListElement>(null);

  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [entries.length]);

  if (entries.length === 0) {
    return <p className="audit__empty">{empty}</p>;
  }

  return (
    <ol ref={listRef} className="audit" aria-live="polite" tabIndex={0} aria-label={label}>
      {entries.map((entry, i) => (
        <li key={`${entry.at}-${i}`} className={`audit__event audit__event--${entry.tone}`}>
          <span className="audit__dot" aria-hidden="true" />
          <div className="audit__line">
            <span className="audit__action">{entry.action}</span>
            <time className="audit__time mono" dateTime={entry.at}>
              {formatClock(entry.at, { seconds: true })}
            </time>
          </div>
          <p className="audit__meta">
            <span className="audit__actor">{entry.actor}</span>
            {entry.detail && ` · ${entry.detail}`}
          </p>
        </li>
      ))}
    </ol>
  );
}
