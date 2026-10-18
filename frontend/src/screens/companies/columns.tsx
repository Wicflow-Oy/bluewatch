// What each company row shows: the sheet's columns on wider screens and one stacked row on phones.
import {
  Building2,
  CalendarDays,
  Clock,
  Hash,
  Layers,
  ListChecks,
  ShieldCheck,
  Tag,
  TrendingUp,
} from "lucide-react";
import type { CompanyRow } from "../../contracts";
import { useT, type Translator } from "../../i18n/messages";
import { formatDay, humanText, registryLabel } from "../../lib/format";
import { verticalText } from "../../lib/labels";
import { Chip, CountryCode, GroupChip } from "../../ui/Chip";
import type { Column } from "../../ui/DataTable";
import { Deadline } from "../../ui/Deadline";
import { evidenceBand, MiniMeter, potentialBand } from "../../ui/Meter";
import { Tooltip } from "../../ui/Tooltip";
import { countryKey, UNKNOWN } from "./filters";
import { companiesMessages, type CompaniesKey } from "./messages";

/** Dates and deadlines sort with the unknown ones last, whichever way the known ones run. */
function byDate(a: string | null | undefined, b: string | null | undefined, newestFirst: boolean) {
  if (!a || !b) return Number(!a) - Number(!b);
  return newestFirst ? b.localeCompare(a) : a.localeCompare(b);
}

interface ScoreCellProps {
  kind: "potential" | "evidence";
  value: number;
}

/** The P/E line with its band word in a tooltip ("High", "Thin"). */
function ScoreCell({ kind, value }: ScoreCellProps) {
  const { t } = useT(companiesMessages);
  const band = kind === "potential" ? potentialBand(value) : evidenceBand(value);
  const label = `${t(kind === "potential" ? "col_potential" : "col_evidence")}: ${band}`;
  return (
    <Tooltip content={label} block>
      <MiniMeter kind={kind} value={value} label={label} />
    </Tooltip>
  );
}

function CountryCell({ code }: { code: string }) {
  const { t } = useT(companiesMessages);
  return countryKey(code) === UNKNOWN ? (
    <Chip tone="hatch">{t("unknown")}</Chip>
  ) : (
    <CountryCode code={code} />
  );
}

function NextStepCell({ row }: { row: CompanyRow }) {
  const { t } = useT(companiesMessages);
  if (!row.next_action) return <span className="sheet__text sheet__muted">{t("noNextStep")}</span>;
  const action = humanText(row.next_action);
  return (
    <span className="sheet__text" title={action}>
      {action}
    </span>
  );
}

/** One fact per column, the way a spreadsheet lays out leads. At 1440px every column fits; narrower
 *  screens scroll the sheet sideways with the row number and the name pinned. */
export function companyColumns(
  t: Translator<CompaniesKey>["t"],
  today: string,
): Column<CompanyRow>[] {
  return [
    {
      id: "company",
      header: t("col_company"),
      icon: Building2,
      width: 220,
      pinned: true,
      cell: (r) => (
        <span className="sheet__name">
          <CountryCell code={r.country} />
          <span className="sheet__name-text" title={r.name}>
            {r.name}
          </span>
        </span>
      ),
    },
    {
      id: "id",
      header: t("col_id"),
      icon: Hash,
      width: 148,
      cell: (r) => (
        <span className="sheet__text mono company-id-cell">
          {registryLabel(r.country, r.registry_id)}
        </span>
      ),
    },
    {
      id: "sector",
      header: t("col_sector"),
      icon: Tag,
      width: { min: 130 },
      cell: (r) => {
        const sector = verticalText(r.vertical, r.vertical_note);
        return sector ? (
          <span className="sheet__text" title={sector}>
            {sector}
          </span>
        ) : (
          <span className="unknown-word">{t("unknown")}</span>
        );
      },
    },
    {
      id: "founded",
      header: t("col_founded"),
      icon: CalendarDays,
      width: 108,
      cell: (r) =>
        r.founded ? (
          <span className="founded-cell mono">{formatDay(r.founded, { year: true })}</span>
        ) : (
          <span className="unknown-word">{t("unknown")}</span>
        ),
      sort: (a, b) => byDate(a.founded, b.founded, true),
    },
    {
      id: "group",
      header: t("col_group"),
      icon: Layers,
      width: 120,
      cell: (r) => <GroupChip group={r.group} />,
    },
    {
      id: "potential",
      header: t("col_potential"),
      icon: TrendingUp,
      width: 108,
      cell: (r) => <ScoreCell kind="potential" value={r.potential} />,
      sort: (a, b) => b.potential - a.potential,
    },
    {
      id: "evidence",
      header: t("col_evidence"),
      icon: ShieldCheck,
      width: 108,
      cell: (r) => <ScoreCell kind="evidence" value={r.evidence} />,
      sort: (a, b) => b.evidence - a.evidence,
    },
    {
      id: "deadline",
      header: t("col_deadline"),
      icon: Clock,
      width: 160,
      cell: (r) => <Deadline date={r.deadline} today={today} />,
      sort: (a, b) => byDate(a.deadline, b.deadline, false),
    },
    {
      id: "next",
      header: t("col_next"),
      icon: ListChecks,
      width: { min: 200, fr: 2 },
      cell: (r) => <NextStepCell row={r} />,
    },
  ];
}

/** Phones: name and group, then country, founding date and vertical, then the next step. */
export function StackedRow({ row }: { row: CompanyRow }) {
  const { t } = useT(companiesMessages);
  const vertical = verticalText(row.vertical, row.vertical_note);
  return (
    <>
      <span className="company-stack__top">
        <span className="company-stack__name">{row.name}</span>
        <GroupChip group={row.group} />
      </span>
      <span className="company-stack__meta">
        <CountryCell code={row.country} />
        <span>
          {row.founded
            ? t("foundedOn", { date: formatDay(row.founded, { year: true }) })
            : t("foundedUnknown")}
        </span>
        {vertical && <span className="company-stack__vertical">{vertical}</span>}
      </span>
      <span className="company-stack__scores">
        <ScoreCell kind="potential" value={row.potential} />
        <ScoreCell kind="evidence" value={row.evidence} />
      </span>
      <span className="company-stack__next">
        {row.next_action ? t("nextStep", { action: humanText(row.next_action) }) : t("noNextStep")}
      </span>
    </>
  );
}
