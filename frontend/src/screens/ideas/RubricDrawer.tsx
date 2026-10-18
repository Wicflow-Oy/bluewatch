// "How we vet": every criterion, weight, rung and rule on one screen, straight from /api/ideas/rubric.
import { RefreshCw, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { useLang } from "../../i18n/lang";
import { useT } from "../../i18n/messages";
import { Drawer } from "../../ui/Drawer";
import { ErrorState, LoadingRegion, SkeletonLines } from "../../ui/States";
import { ideasApi } from "./api";
import { CloseButton } from "./CloseButton";
import { ideasMessages } from "./messages";
import { readMessages } from "./read/messages";
import type { RubricInfo } from "./types";

interface Loaded {
  attempt: number;
  lang: string;
  rubric: RubricInfo | null;
}

/**
 * Loads the rubric the first time the drawer opens, and again in a new language: the rubric itself
 * never changes while the page is open.
 */
function useRubric(open: boolean) {
  const lang = useLang();
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const wanted = open && (loaded?.rubric == null || loaded.lang !== lang);

  useEffect(() => {
    if (!wanted) return;
    let current = true;
    ideasApi.rubric().then(
      (rubric) => current && setLoaded({ attempt, lang, rubric }),
      () => current && setLoaded((last) => ({ attempt, lang, rubric: last?.rubric ?? null })),
    );
    return () => {
      current = false;
    };
  }, [wanted, attempt, lang]);

  return {
    rubric: loaded?.rubric ?? null,
    failed: loaded !== null && loaded.rubric === null && loaded.attempt === attempt,
    retry: () => setAttempt((n) => n + 1),
  };
}

const AXES = ["potential", "evidence"] as const;

interface RubricDrawerProps {
  open: boolean;
  onClose: () => void;
  /** The queue's note on outcome data, shown with the tiers once the queue has loaded. */
  baseRateNote: string | null;
}

export function RubricDrawer({ open, onClose, baseRateNote }: RubricDrawerProps) {
  const { t } = useT(ideasMessages);
  const { rubric, failed, retry } = useRubric(open);
  return (
    <Drawer open={open} onClose={onClose} label={t("rubricTitle")}>
      <div className="ih-cardview">
        <header className="ih-cardview__head ih-cardview__head--ruled">
          <div className="ih-cardview__top">
            <div>
              <h2 className="ih-cardview__title t-h2">{t("rubricTitle")}</h2>
              {rubric && <p className="ih-caption mono">{rubric.version}</p>}
            </div>
            <CloseButton onClose={onClose} />
          </div>
        </header>
        <div className="ih-cardview__body">
          {rubric ? (
            <RubricBody rubric={rubric} baseRateNote={baseRateNote} />
          ) : failed ? (
            <ErrorState
              compact
              icon={<TriangleAlert size={20} strokeWidth={1.5} aria-hidden="true" />}
              title={t("rubricFailed")}
              action={
                <button type="button" className="btn" onClick={retry}>
                  <RefreshCw size={16} strokeWidth={1.5} aria-hidden="true" />
                  {t("retry")}
                </button>
              }
            >
              {t("rubricFailedBody")}
            </ErrorState>
          ) : (
            <LoadingRegion label={t("loadingRubric")}>
              <SkeletonLines lines={8} gap={12} />
            </LoadingRegion>
          )}
        </div>
      </div>
    </Drawer>
  );
}

function RubricBody({ rubric, baseRateNote }: { rubric: RubricInfo; baseRateNote: string | null }) {
  const { t } = useT(ideasMessages);
  const axis = useT(readMessages);
  return (
    <div className="ih-rubric">
      <table className="ih-rubric__table">
        <thead>
          <tr>
            <th>{t("col_criterion")}</th>
            <th className="ih-rubric__weight">{t("col_weight")}</th>
            <th>{t("col_rungs")}</th>
            <th>{t("col_rule")}</th>
          </tr>
        </thead>
        {AXES.map((name) => (
          <tbody key={name}>
            <tr className="ih-rubric__axis">
              <th colSpan={4} scope="rowgroup">
                {axis.t(name)}
              </th>
            </tr>
            {rubric.criteria
              .filter((c) => c.axis === name)
              .map((c) => (
                <tr key={c.id}>
                  <th scope="row" className="ih-rubric__label">
                    {c.label}
                  </th>
                  <td className="ih-rubric__weight mono">
                    <span className="ih-rubric__key">{t("col_weight")} </span>
                    {c.weight}
                  </td>
                  <td className="ih-rubric__rungs">{c.rungs.join(" · ")}</td>
                  <td className="ih-rubric__rule">{c.rule}</td>
                </tr>
              ))}
          </tbody>
        ))}
      </table>

      <section className="ih-box ih-rubric__section">
        <h3 className="ih-box__title">{axis.t("potential")}</h3>
        <p>{rubric.potential_rule}</p>
      </section>
      <section className="ih-box ih-rubric__section">
        <h3 className="ih-box__title">{axis.t("evidence")}</h3>
        <p>{rubric.evidence_rule}</p>
      </section>
      <section className="ih-box ih-rubric__section">
        <h3 className="ih-box__title">{t("tiers")}</h3>
        <p className="ih-caption">{t("firstMatchWins")}</p>
        <ol className="ih-numbered">
          {rubric.tier_rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ol>
      </section>
      <section className="ih-box ih-rubric__section">
        <h3 className="ih-box__title">{t("antiGaming")}</h3>
        <ul className="ih-bullets">
          {rubric.anti_gaming.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </section>
      {/* The queue's note opens with the same "rules, not predictions" sentence, so it replaces it. */}
      <p className="ih-rubric__footer">
        {baseRateNote ?? t("rulesNotPredictions")} {t("personReviews")}
      </p>
    </div>
  );
}
