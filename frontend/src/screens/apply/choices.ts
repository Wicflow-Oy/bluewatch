import type { Option } from "../ideas/types";

/** A form option with its enum value typed. */
export interface Choice<T extends string> {
  value: T;
  label: string;
  hint: string;
}

/**
 * The API sends each option's enum value as a plain string. This is the one place it is typed as the
 * enum: the values come from the same server that validates them on the way back.
 */
export function asChoices<T extends string>(options: Option[]): Choice<T>[] {
  return options.map((o) => ({ value: o.value as T, label: o.label, hint: o.hint }));
}
