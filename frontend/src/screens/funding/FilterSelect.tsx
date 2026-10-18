import { ChevronDown } from "lucide-react";

export interface SelectOption<T extends string> {
  value: T;
  label: string;
}

interface FilterSelectProps<T extends string> {
  label: string;
  value: T;
  options: SelectOption<T>[];
  onChange: (value: T) => void;
  className?: string;
}

/** A native select (keyboard and phone pickers for free) that reads "Kind  All kinds ▾". */
export function FilterSelect<T extends string>({
  label,
  value,
  options,
  onChange,
  className,
}: FilterSelectProps<T>) {
  return (
    <label className={`filter-select${className ? ` ${className}` : ""}`}>
      <span className="filter-select__label">{label}</span>
      <select
        className="filter-select__control"
        value={value}
        onChange={(e) => {
          const next = options.find((o) => o.value === e.target.value);
          if (next) onChange(next.value);
        }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown size={14} strokeWidth={1.5} aria-hidden="true" />
    </label>
  );
}
