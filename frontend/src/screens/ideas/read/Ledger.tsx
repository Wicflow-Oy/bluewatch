// The ledger keeps four kinds of statement apart: facts someone can open, claims in the team's own
// words, our assumptions with their basis, and unknowns with the check that would close them.
import { ChevronDown, ExternalLink } from "lucide-react";
import type { ReactNode } from "react";
import { useT } from "../../../i18n/messages";
import type { IdeaLedger, LedgerItem } from "../types";
import { readableDates, useToday } from "./hooks";
import { readMessages } from "./messages";
import "./read.css";

type Group = keyof IdeaLedger;

const ORDER: Group[] = ["facts", "claims", "assumptions", "unknowns"];

const SWATCH: Record<Group, string> = {
  facts: "ih-swatch--fact",
  claims: "ih-swatch--claim",
  assumptions: "ih-swatch--assumption",
  unknowns: "ih-swatch--unknown",
};

/** The team's view: four groups with counts, open on a wide screen and an accordion on a phone. */
export function LedgerGroups({ ledger, open }: { ledger: IdeaLedger; open: boolean }) {
  const { t } = useT(readMessages);
  // The team reads its own claims and our assumptions, so those two titles say whose they are.
  const title = (group: Group) =>
    group === "claims" || group === "assumptions"
      ? t(`studentLedger_${group}`)
      : t(`ledger_${group}`);
  return (
    <div className="ih-ledger-groups">
      {ORDER.map((group) => (
        <details key={group} className="ih-ledger-group" open={open}>
          <summary className="ih-ledger-group__summary">
            <span className={`ih-swatch ${SWATCH[group]}`} aria-hidden="true" />
            <span className="ih-ledger-group__title">{title(group)}</span>
            <span className="ih-count mono">{ledger[group].length}</span>
            <ChevronDown className="ih-chev" size={14} strokeWidth={1.75} aria-hidden="true" />
          </summary>
          <LedgerItems
            items={ledger[group]}
            empty={group === "facts" ? t("studentNoFacts") : emptyText(group, t)}
          >
            {(item) => <StudentEntry group={group} item={item} />}
          </LedgerItems>
        </details>
      ))}
    </div>
  );
}

/** A'Pelago's view: four columns (two by two in the drawer, stacked on a phone). */
export function LedgerColumns({ ledger }: { ledger: IdeaLedger }) {
  const { t } = useT(readMessages);
  return (
    <div className="ih-ledger-columns">
      {ORDER.map((group) => (
        <section key={group} className="ih-ledger-column" aria-label={t(`ledger_${group}`)}>
          <h3 className="ih-ledger-column__title">
            <span className={`ih-swatch ${SWATCH[group]}`} aria-hidden="true" />
            {t(`ledger_${group}`)}
            <span className="ih-count mono">{ledger[group].length}</span>
          </h3>
          <LedgerItems items={ledger[group]} empty={emptyText(group, t)}>
            {(item) => <ReviewerEntry group={group} item={item} />}
          </LedgerItems>
        </section>
      ))}
    </div>
  );
}

function emptyText(group: Group, t: (key: "ledgerNothingOpen" | "ledgerNone") => string): string {
  return t(group === "unknowns" ? "ledgerNothingOpen" : "ledgerNone");
}

function LedgerItems({
  items,
  empty,
  children,
}: {
  items: LedgerItem[];
  empty: string;
  children: (item: LedgerItem) => ReactNode;
}) {
  if (items.length === 0) return <p className="ih-ledger__empty">{empty}</p>;
  return (
    <ul className="ih-ledger__items">
      {items.map((item) => (
        <li key={item.id} className="ih-ledger__item">
          {children(item)}
        </li>
      ))}
    </ul>
  );
}

function StudentEntry({ group, item }: { group: Group; item: LedgerItem }) {
  const { t } = useT(readMessages);
  const question = item.next_check?.question;
  return (
    <>
      <p className="ih-ledger__text">{item.text}</p>
      {item.quote && <q className="ih-quote">{item.quote}</q>}
      {group === "claims" && <p className="ih-caption">{item.source}</p>}
      {group === "assumptions" && item.basis && (
        <p className="ih-caption">{t("whyAssumed", { basis: item.basis })}</p>
      )}
      {group === "unknowns" && question && (
        <p className="ih-ledger__check">{t("nextCheck", { question })}</p>
      )}
    </>
  );
}

function ReviewerEntry({ group, item }: { group: Group; item: LedgerItem }) {
  const { t } = useT(readMessages);
  const today = useToday();
  const question = item.next_check?.question;
  return (
    <>
      <p className="ih-ledger__text">{readableDates(item.text, today)}</p>
      {group === "facts" && item.source_url && (
        <a className="ih-link" href={item.source_url} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={12} strokeWidth={1.5} aria-hidden="true" />
          {item.source}
        </a>
      )}
      {group === "facts" && !item.source_url && <p className="ih-caption">{item.source}</p>}
      {item.quote && <q className="ih-quote">{item.quote}</q>}
      {group === "claims" && <p className="ih-caption">{item.source}</p>}
      {group === "assumptions" && item.basis && <p className="ih-caption">{item.basis}</p>}
      {group === "unknowns" && question && (
        <p className="ih-ledger__check">{t("askQuestion", { question })}</p>
      )}
    </>
  );
}
