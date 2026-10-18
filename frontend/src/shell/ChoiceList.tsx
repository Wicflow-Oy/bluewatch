// One-of-n choices with a line of explanation each: the preset and the workspace, in the top-bar
// popover and in the phone's More sheet. Arrow keys move between options; Enter or Space picks one.
import { Check } from "lucide-react";
import { useRef, type KeyboardEvent, type ReactNode } from "react";
import "./ChoiceList.css";

export interface Choice<T extends string> {
  value: T;
  title: string;
  description?: string;
  leading?: ReactNode;
}

interface ChoiceListProps<T extends string> {
  label: string;
  choices: Choice<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Focus the selected option on mount (a popover that just opened). */
  autoFocus?: boolean;
}

export function ChoiceList<T extends string>({
  label,
  choices,
  value,
  onChange,
  autoFocus = false,
}: ChoiceListProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const at = refs.current.findIndex((el) => el === document.activeElement);
    const step = e.key === "ArrowDown" ? 1 : -1;
    refs.current[(at + step + choices.length) % choices.length]?.focus();
  };

  return (
    <div className="choices" role="radiogroup" aria-label={label} onKeyDown={onKeyDown}>
      {choices.map((choice, i) => {
        const checked = choice.value === value;
        return (
          <button
            key={choice.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={checked}
            className="choice"
            autoFocus={autoFocus && checked}
            onClick={() => onChange(choice.value)}
          >
            {choice.leading}
            <span className="choice__text">
              <span className="choice__title">{choice.title}</span>
              {choice.description && (
                <span className="choice__description">{choice.description}</span>
              )}
            </span>
            <span className="choice__check" aria-hidden="true">
              {checked && <Check size={16} strokeWidth={1.75} />}
            </span>
          </button>
        );
      })}
    </div>
  );
}
