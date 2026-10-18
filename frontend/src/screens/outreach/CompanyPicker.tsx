// Only companies matched to their register record with certainty can be asked anything, so the picker
// offers the listed ones that are resolved (plus the company handed over, so the choice stays visible).
import { use, useId } from "react";
import { load } from "../../data";
import { useT } from "../../i18n/messages";
import { companyIdLabel } from "../../lib/format";
import { usePreset } from "../../lib/preset";
import { useWorkspace } from "../../lib/workspace";
import { Skeleton } from "../../ui/States";
import { outreachMessages } from "./messages";

interface CompanyPickerProps {
  value: string;
  onChange(companyId: string): void;
}

export function CompanyPicker({ value, onChange }: CompanyPickerProps) {
  const { t } = useT(outreachMessages);
  const { mode } = useWorkspace();
  const { preset } = usePreset();
  const rows = use(load.companies(mode, preset)).data;
  const listed = new Set(use(load.list(mode, preset)).data.entries.map((e) => e.company_id));
  const options = rows.filter(
    (r) => r.id === value || (r.resolution === "resolved" && listed.has(r.id)),
  );
  const id = useId();

  return (
    <div className="outreach-picker">
      <label className="sr-only" htmlFor={id}>
        {t("company")}
      </label>
      <select
        id={id}
        className="outreach-picker__select select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {!options.some((o) => o.id === value) && (
          <option value={value}>{companyIdLabel(value)}</option>
        )}
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </div>
  );
}

export function CompanyPickerSkeleton() {
  return <Skeleton width={280} height={36} radius={999} />;
}
