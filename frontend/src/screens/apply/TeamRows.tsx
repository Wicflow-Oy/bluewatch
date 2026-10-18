// The team as roles with optional skills, one row per person and never a name.
import { Plus, X } from "lucide-react";
import { useT } from "../../i18n/messages";
import type { Role } from "../ideas/types";
import type { Choice } from "./choices";
import type { TeamRow } from "./draft";
import { applyMessages } from "./messages";

interface TeamRowsProps {
  rows: TeamRow[];
  roles: Choice<Role>[];
  maxRows: number;
  skillsLimit: number;
  onChange: (rows: TeamRow[]) => void;
}

export function TeamRows({ rows, roles, maxRows, skillsLimit, onChange }: TeamRowsProps) {
  const { t } = useT(applyMessages);
  const update = (index: number, row: TeamRow) =>
    onChange(rows.map((r, i) => (i === index ? row : r)));
  return (
    <div className="ap-team">
      <ul className="ap-team__rows">
        {rows.map((row, index) => {
          const hint = roles.find((r) => r.value === row.role)?.hint;
          return (
            <li
              key={index}
              className={rows.length > 1 ? "ap-team__row ap-team__row--removable" : "ap-team__row"}
            >
              <div className="ap-team__role">
                <label className="ap-field__label" htmlFor={`ap-role-${index}`}>
                  {t("role")}
                </label>
                <select
                  id={`ap-role-${index}`}
                  className="input"
                  value={row.role}
                  onChange={(e) =>
                    update(index, {
                      ...row,
                      role: roles.find((r) => r.value === e.target.value)?.value ?? "",
                    })
                  }
                >
                  <option value="">{t("chooseRole")}</option>
                  {roles.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
                {hint && <p className="ap-field__helper">{hint}</p>}
              </div>
              <div className="ap-team__skills">
                <label className="ap-field__label" htmlFor={`ap-skills-${index}`}>
                  {t("skills")}
                </label>
                <input
                  id={`ap-skills-${index}`}
                  className="input"
                  value={row.skills}
                  maxLength={skillsLimit}
                  onChange={(e) => update(index, { ...row, skills: e.target.value })}
                />
              </div>
              {rows.length > 1 && (
                <button
                  type="button"
                  className="icon-btn ap-team__remove"
                  aria-label={t("removeRole")}
                  onClick={() => onChange(rows.filter((_, i) => i !== index))}
                >
                  <X size={16} strokeWidth={1.5} aria-hidden="true" />
                </button>
              )}
            </li>
          );
        })}
      </ul>
      <p className="ap-field__helper">{t("skillsExample")}</p>
      {rows.length < maxRows && (
        <button
          type="button"
          className="btn btn--subtle btn--sm ap-add"
          onClick={() => onChange([...rows, { role: "", skills: "" }])}
        >
          <Plus size={16} strokeWidth={1.5} aria-hidden="true" />
          {t("addRole")}
        </button>
      )}
    </div>
  );
}
