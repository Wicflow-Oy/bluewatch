// Programmes, grants and pilots that fit the company, each with its tier and deadline.
import { GraduationCap } from "lucide-react";
import type { Mode } from "../../api";
import type { Opportunity } from "../../contracts";
import { useT } from "../../i18n/messages";
import { stepKindLabel } from "../../lib/labels";
import { TierChip } from "../../ui/Chip";
import { Deadline } from "../../ui/Deadline";
import { Panel } from "../../ui/Panel";
import { founderMessages } from "./messages";

interface ProgrammesProps {
  programmes: Opportunity[];
  /** The company's name, when the register gives one. */
  name: string | null | undefined;
  mode: Mode;
  today: string;
}

export function Programmes({ programmes, name, mode, today }: ProgrammesProps) {
  const { t, tn } = useT(founderMessages);
  return (
    <Panel
      className="founder-result__programmes"
      icon={<GraduationCap size={16} strokeWidth={1.5} aria-hidden="true" />}
      title={t("programmesTitle")}
      meta={<span className="mono">{tn("programmes", programmes.length)}</span>}
    >
      {programmes.length === 0 ? (
        <p className="muted">{name ? t("noProgrammesNamed", { name }) : t("noProgrammes")}</p>
      ) : (
        <ul className="founder-list">
          {programmes.map((programme) => (
            <li key={programme.id} className="founder-list__row founder-list__row--wrap">
              <div className="founder-list__text">
                <span className="founder-list__name">{programme.title}</span>
                <span className="founder-list__detail">{stepKindLabel(programme.kind)}</span>
              </div>
              <div className="founder-list__end">
                {programme.tier && <TierChip tier={programme.tier} mode={mode} />}
                {programme.deadline && <Deadline date={programme.deadline} today={today} />}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
