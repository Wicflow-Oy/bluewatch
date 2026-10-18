// One level's confusion matrix: answer key bands down, ours across, a single hue by count so the
// eye finds the diagonal without a red-green verdict.
import { useT } from "../../i18n/messages";
import { precisionMessages } from "./messages";
import { useBandText } from "./useBandText";

interface ConfusionMatrixProps {
  confusion: Record<string, Record<string, number>>;
  /** The level's name, for the table's caption. */
  label: string;
}

export function ConfusionMatrix({ confusion, label }: ConfusionMatrixProps) {
  const { t } = useT(precisionMessages);
  const bandText = useBandText();
  const rows = Object.keys(confusion);
  const columns = [...new Set(rows.flatMap((row) => Object.keys(confusion[row])))];
  const max = Math.max(1, ...rows.flatMap((row) => Object.values(confusion[row])));

  return (
    <table className="matrix">
      <caption className="sr-only">{t("matrixSummary", { level: label })}</caption>
      <thead>
        <tr>
          <th scope="col" rowSpan={2} className="matrix__corner">
            {t("answerKey")}
          </th>
          <th scope="colgroup" colSpan={columns.length} className="matrix__axis">
            {t("ours")}
          </th>
        </tr>
        <tr>
          {columns.map((column) => (
            <th key={column} scope="col" className="matrix__band">
              {bandText(column)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row}>
            <th scope="row" className="matrix__band">
              {bandText(row)}
            </th>
            {columns.map((column) => {
              const count = confusion[row][column] ?? 0;
              const fill = count > 0 ? Math.floor((0.12 + (0.7 * count) / max) * 100) : 0;
              const classes = [
                "matrix__cell mono",
                row === column && "matrix__cell--diagonal",
                fill >= 50 && "matrix__cell--strong",
              ];
              return (
                <td
                  key={column}
                  className={classes.filter(Boolean).join(" ")}
                  style={
                    fill > 0
                      ? { background: `color-mix(in srgb, var(--accent) ${fill}%, var(--surface))` }
                      : undefined
                  }
                >
                  {count}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
