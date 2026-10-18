// Our agreement next to the age baseline's, both out of the same n. Neither side is framed as good or
// bad: the higher one is underlined, a tie underlines nothing.
import { useT } from "../i18n/messages";
import { trunc } from "../lib/format";
import { Chip } from "./Chip";
import { CountUp } from "./CountUp";
import { uiMessages } from "./messages";
import "./StatPair.css";

interface StatPairProps {
  label: string;
  /** What the two numbers count, under the label. */
  measure?: string;
  ours: number | null;
  baseline: number | null;
  n: number;
  /** The 95% interval of our share; leave it out when there is none to show. */
  interval?: [number, number] | null;
}

export function StatPair({ label, measure, ours, baseline, n, interval }: StatPairProps) {
  const { t } = useT(uiMessages);
  const leader =
    ours === null || baseline === null || ours === baseline
      ? null
      : ours > baseline
        ? "ours"
        : "baseline";
  return (
    <figure className="stat-pair">
      <figcaption className="stat-pair__label">
        {label}
        {measure && <span className="stat-pair__measure">{measure}</span>}
      </figcaption>
      <dl className="stat-pair__values">
        <StatValue term={t("statOurs")} value={ours} n={n} leads={leader === "ours"} />
        <StatValue
          term={t("statAgeBaseline")}
          value={baseline}
          n={n}
          leads={leader === "baseline"}
        />
      </dl>
      {interval && (
        <p className="stat-pair__interval">
          {t("statInterval")}{" "}
          <span className="mono">
            {trunc(interval[0])}–{trunc(interval[1])}
          </span>
        </p>
      )}
    </figure>
  );
}

interface StatValueProps {
  term: string;
  value: number | null;
  n: number;
  leads: boolean;
}

function StatValue({ term, value, n, leads }: StatValueProps) {
  const { t } = useT(uiMessages);
  return (
    <div className="stat-pair__side">
      <dt className="stat-pair__term">{term}</dt>
      <dd className={`stat-pair__value${leads ? " stat-pair__value--leads" : ""}`}>
        {value === null ? (
          <Chip tone="hatch">{t("state_unknown")}</Chip>
        ) : (
          <span className="mono">
            <span className="stat-pair__k">
              <CountUp value={value} decimals={0} />
            </span>
            <span className="stat-pair__of">{t("outOf", { n })}</span>
          </span>
        )}
        {leads && <span className="sr-only"> {t("statHigher")}</span>}
      </dd>
    </div>
  );
}
