// A company's move between two rankings of the same list: "↑3", "↓1", "New" or "–".
import { useT } from "../i18n/messages";
import { uiMessages } from "./messages";
import "./RankDelta.css";

interface RankDeltaProps {
  /** The rank in the list it is compared with; null when it was not in that list. */
  before: number | null;
  after: number;
}

export function RankDelta({ before, after }: RankDeltaProps) {
  const { t, tn } = useT(uiMessages);
  if (before === null) {
    return <span className="rank-delta rank-delta--new">{t("changeNew")}</span>;
  }
  const moved = before - after;
  if (moved === 0) {
    return (
      <span className="rank-delta rank-delta--same">
        <span aria-hidden="true">–</span>
        <span className="sr-only">{t("rankSame")}</span>
      </span>
    );
  }
  const up = moved > 0;
  const places = Math.abs(moved);
  return (
    <span className={`rank-delta mono rank-delta--${up ? "up" : "down"}`}>
      <span aria-hidden="true">{`${up ? "↑" : "↓"}${places}`}</span>
      <span className="sr-only">{tn(up ? "rankUp" : "rankDown", places, { before })}</span>
    </span>
  );
}
