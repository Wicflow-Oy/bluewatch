// Each company of a blind set side by side: our call, the partner's, and how far apart they are.
import { useT } from "../../i18n/messages";
import { useMeta } from "../../lib/meta";
import { Chip, type Tone } from "../../ui/Chip";
import { uiMessages } from "../../ui/messages";
import { precisionMessages } from "./messages";
import type { PartnerCall, PartnerLevel, PartnerRow, Verdict } from "./model";
import { useBandText } from "./useBandText";

const PARTNER_LEVELS: PartnerLevel[] = ["TRL", "BRL", "stage"];

export function PartnerTable({ rows }: { rows: PartnerRow[] }) {
  const { t } = useT(precisionMessages);
  const meta = useMeta();
  const headers: Record<PartnerLevel, string> = {
    TRL: meta.level("trl"),
    BRL: meta.level("brl"),
    stage: t("investmentStage"),
  };
  return (
    <table className="partner-table">
      <caption className="sr-only">{t("partnerCaption")}</caption>
      <thead>
        <tr>
          <th scope="col">{t("company")}</th>
          {PARTNER_LEVELS.map((level) => (
            <th key={level} scope="col">
              {headers[level]}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.name}>
            <th scope="row">{row.name}</th>
            {row.matched ? (
              PARTNER_LEVELS.map((level) => (
                <td key={level} data-label={headers[level]}>
                  <CallCell call={row.calls[level]} />
                </td>
              ))
            ) : (
              <td colSpan={PARTNER_LEVELS.length} className="partner-table__unmatched">
                {t("notAssessed")}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const VERDICT = {
  "same band": { tone: "teal", key: "verdict_same" },
  "within one": { tone: "blue", key: "verdict_within" },
  differs: { tone: "grey", key: "verdict_differs" },
} as const satisfies Record<Verdict, { tone: Tone; key: string }>;

function CallCell({ call }: { call: PartnerCall | undefined }) {
  const { t } = useT(precisionMessages);
  if (!call) return <span className="partner-table__none">{t("noCalls")}</span>;
  const verdict = call.verdict && VERDICT[call.verdict];
  return (
    <div className="partner-call">
      <span>
        {t("ourCall")} <CallValue value={call.ours} />
      </span>
      <span>
        {t("yourCall")} <CallValue value={call.theirs} />
      </span>
      {verdict && <Chip tone={verdict.tone}>{t(verdict.key)}</Chip>}
    </div>
  );
}

function CallValue({ value }: { value: string }) {
  const ui = useT(uiMessages);
  const bandText = useBandText();
  if (value === "unknown") return <Chip tone="hatch">{ui.t("state_unknown")}</Chip>;
  // Levels and bands are figures; stage words are words.
  return (
    <span className={/\d/.test(value) ? "mono partner-call__value" : "partner-call__value"}>
      {bandText(value)}
    </span>
  );
}
