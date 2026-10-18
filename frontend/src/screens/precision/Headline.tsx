// The honest sentence at the top: where the age baseline beats our rules, said first and computed
// from the levels, so it changes the moment the numbers do.
import { Scale } from "lucide-react";
import type { LevelAgreement } from "../../contracts";
import { localeOf, useT } from "../../i18n/messages";
import { useLang } from "../../i18n/lang";
import { formatStamp } from "../../lib/format";
import { useMeta } from "../../lib/meta";
import { Chip } from "../../ui/Chip";
import { Panel } from "../../ui/Panel";
import { precisionMessages } from "./messages";
import { agreementUnit, compareWithBaseline, sentenceLabel, type Comparison } from "./model";
import { Figure, Rich } from "./Rich";

interface HeadlineProps {
  levels: LevelAgreement[];
  /** The A'Pelago word for a level, which the sentence uses in both workspaces. */
  apelagoLabel(key: string): string;
  generatedAt: string;
  recorded: boolean;
}

export function Headline({ levels, apelagoLabel, generatedAt, recorded }: HeadlineProps) {
  const { t } = useT(precisionMessages);
  const { baselineAhead, oursAhead, tied } = compareWithBaseline(levels);
  const tone = baselineAhead.length > 0 ? "amber" : oursAhead.length > 0 ? "teal" : "plain";
  const nothingToCompare = baselineAhead.length + oursAhead.length + tied.length === 0;
  const clauses = (rows: Comparison[], leader: Leader) => (
    <Clauses rows={rows} leader={leader} apelagoLabel={apelagoLabel} />
  );

  return (
    <Panel
      title={t("headlineTitle")}
      icon={<Scale size={16} strokeWidth={1.5} aria-hidden="true" />}
      className={`precision__full precision-headline precision-headline--${tone}`}
      actions={<RunStamp generatedAt={generatedAt} recorded={recorded} />}
    >
      <div className="precision-headline__text">
        {baselineAhead.length > 0 && (
          <p className="precision-headline__lead">
            <Rich
              text={t("baselineAhead")}
              values={{ levels: clauses(baselineAhead, "baseline") }}
            />
          </p>
        )}
        {oursAhead.length > 0 && (
          <p
            className={
              baselineAhead.length > 0 ? "precision-headline__more" : "precision-headline__lead"
            }
          >
            <Rich
              text={t(baselineAhead.length > 0 ? "oursAheadToo" : "oursAhead")}
              values={{ levels: clauses(oursAhead, "ours") }}
            />
          </p>
        )}
        {tied.length > 0 && (
          <p className="precision-headline__more">
            <Rich text={t("tied")} values={{ levels: clauses(tied, "ours") }} />
          </p>
        )}
        {nothingToCompare && <p className="precision-headline__lead">{t("nothingToCompare")}</p>}
        <p className="precision-headline__caveat">{t("smallN")}</p>
      </div>
    </Panel>
  );
}

/** When the numbers were computed; a recorded run (the demo-data fallback) says so. */
function RunStamp({ generatedAt, recorded }: { generatedAt: string; recorded: boolean }) {
  const { t } = useT(precisionMessages);
  const stamp = <span className="mono">{formatStamp(generatedAt)}</span>;
  return recorded ? (
    <Chip>
      {t("recorded")} {stamp}
    </Chip>
  ) : (
    <span className="precision__stamp t-meta">
      {t("computed")} {stamp}
    </span>
  );
}

type Leader = "ours" | "baseline";

/** "business readiness (15 vs 14 of 28 in the same band) and investment readiness (5 vs 1 of 10 at the
 * same stage)". */
function Clauses({
  rows,
  leader,
  apelagoLabel,
}: {
  rows: Comparison[];
  leader: Leader;
  apelagoLabel(key: string): string;
}) {
  const { t } = useT(precisionMessages);
  const { mode } = useMeta();
  const lang = useLang();
  // The list is joined by placeholder index, so each language puts its own commas and "and".
  const parts = new Intl.ListFormat(localeOf(lang), { type: "conjunction" }).formatToParts(
    rows.map((_, i) => String(i)),
  );
  return parts.map((part, i) => {
    if (part.type === "literal") return part.value;
    const row = rows[Number(part.value)];
    const [first, second] = leader === "ours" ? [row.ours, row.baseline] : [row.baseline, row.ours];
    return (
      <Rich
        key={i}
        text={t(`clause_${agreementUnit(row.key)}`)}
        values={{
          level: sentenceLabel(row.key, apelagoLabel(row.key), mode),
          first: <Figure>{first}</Figure>,
          second: <Figure>{second}</Figure>,
          n: <Figure>{row.n}</Figure>,
        }}
      />
    );
  });
}
