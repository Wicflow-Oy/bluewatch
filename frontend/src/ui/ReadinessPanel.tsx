// The four readiness levels, each with how sure we are and how to raise it. An unknown level is hatched,
// never drawn as zero. A'Pelago reports ocean impact with the Ocean Impact Navigator, so in that
// workspace the impact row shows area tags and never a number.
import { Waves } from "lucide-react";
import type { Mode } from "../api";
import type { ReadinessLevel } from "../contracts";
import { useT, type Translator } from "../i18n/messages";
import { levelText } from "../lib/format";
import { useMeta } from "../lib/meta";
import { Chip } from "./Chip";
import { uiMessages } from "./messages";
import { ConfidenceDots, ReadinessTrack } from "./Readiness";
import { readinessPanelMessages } from "./ReadinessPanel.messages";
import "./ReadinessPanel.css";

const ORDER: ReadinessLevel["key"][] = ["trl", "brl", "oirl", "irl"];
const IMPACT_MAX = 5;
const LEVEL_MAX = 9;

type PanelText = Translator<keyof typeof readinessPanelMessages.en>["t"];

/** Backend reasons sometimes end in a full stop; the row adds its own punctuation. Levels inside them
 * are worded for the workspace. */
function clause(text: string, mode: Mode): string {
  return levelText(text.trim().replace(/\.$/, ""), mode);
}

function raiseLine(level: ReadinessLevel, t: PanelText, mode: Mode): string | null {
  return level.raise_by ? t("raiseWith", { how: clause(level.raise_by, mode) }) : null;
}

function noteFor(level: ReadinessLevel, t: PanelText, mode: Mode): string | null {
  if (level.applicable === false) return level.unknown_reason ?? null;
  const raise = raiseLine(level, t, mode);
  if (level.level == null && level.unknown_reason) {
    const unknown = t("unknownBecause", { reason: clause(level.unknown_reason, mode) });
    return raise ? `${unknown} ${raise}` : unknown;
  }
  return raise;
}

function AreaTags({ areas }: { areas: string[] }) {
  return (
    <div className="readiness__areas">
      {areas.map((area) => (
        <Chip key={area} icon={<Waves size={12} strokeWidth={1.5} aria-hidden="true" />}>
          {area}
        </Chip>
      ))}
    </div>
  );
}

/** A'Pelago's impact row: area tags, never a level number. */
function ImpactAreas({ level }: { level: ReadinessLevel }) {
  const { t } = useT(readinessPanelMessages);
  const areas = level.areas ?? [];
  if (areas.length === 0) {
    const raise = raiseLine(level, t, "apelago");
    return (
      <div className="readiness__impact">
        <span className="readiness__no-area">{t("noImpactArea")}</span>
        {raise && <p className="readiness__note">{raise}</p>}
      </div>
    );
  }
  // Areas without a level were inferred from what the company does, not read from an impact claim.
  const inferred = level.level == null;
  return (
    <div className="readiness__impact">
      <AreaTags areas={areas} />
      {inferred && <p className="readiness__note">{t("areasInferred")}</p>}
      {level.thesis_quote && (
        <p className="readiness__note">
          {t("ownWords")} <q className="readiness__quote">{level.thesis_quote}</q>
        </p>
      )}
    </div>
  );
}

function LevelState({ level, max }: { level: ReadinessLevel; max: number }) {
  const { t } = useT(readinessPanelMessages);
  const ui = useT(uiMessages);
  const known = level.level != null;
  const text =
    level.applicable === false
      ? ui.t("state_not_applicable")
      : level.level != null
        ? t("levelOf", { level: level.level, max })
        : ui.t("state_unknown");
  return (
    <span className={`readiness__state mono${known ? "" : " readiness__state--muted"}`}>
      {text}
    </span>
  );
}

function LevelRow({ level, mode }: { level: ReadinessLevel; mode: Mode }) {
  const { t } = useT(readinessPanelMessages);
  const meta = useMeta();
  const label = meta.level(level.key);
  const isImpact = level.key === "oirl";

  if (isImpact && mode === "apelago") {
    return (
      <li className="readiness__row readiness__row--areas">
        <span className="readiness__label">{label}</span>
        <ImpactAreas level={level} />
      </li>
    );
  }

  const max = isImpact ? IMPACT_MAX : LEVEL_MAX;
  const applicable = level.applicable !== false;
  const note = noteFor(level, t, mode);
  const areas = isImpact ? (level.areas ?? []) : [];
  return (
    <li className="readiness__row">
      <span className="readiness__label">{label}</span>
      {applicable ? (
        <ReadinessTrack
          max={max}
          level={level.level}
          band={level.level != null ? level.band : null}
          showNumbers={false}
          label={label}
        />
      ) : (
        <span className="readiness__na" aria-hidden="true" />
      )}
      <LevelState level={level} max={max} />
      <span className="readiness__confidence">
        {applicable && <ConfidenceDots confidence={level.confidence} />}
      </span>
      <div className="readiness__sub">
        {areas.length > 0 && <AreaTags areas={areas} />}
        {note && <p className="readiness__note">{note}</p>}
        {isImpact && <p className="readiness__note readiness__note--faint">{t("draftScale")}</p>}
      </div>
    </li>
  );
}

export function ReadinessPanel({ levels, mode }: { levels: ReadinessLevel[]; mode: Mode }) {
  const { t } = useT(readinessPanelMessages);
  const ordered = ORDER.flatMap((key) => levels.filter((l) => l.key === key));
  return (
    <ul className="readiness" aria-label={t("readinessLevels")}>
      {ordered.map((level) => (
        <LevelRow key={level.key} level={level} mode={mode} />
      ))}
    </ul>
  );
}
