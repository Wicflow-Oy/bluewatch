// Form controls for the student page: a labelled field with helper, error and a counter near the limit,
// an auto-growing textarea, and chip groups that work as radios or checkboxes.
import { Check, CircleAlert } from "lucide-react";
import { useId, useLayoutEffect, useRef, type ReactNode } from "react";
import { useSlidingIndicator } from "../../ui/useSlidingIndicator";
import type { Choice } from "./choices";

interface FieldProps {
  label: ReactNode;
  helper?: ReactNode;
  error?: string;
  /** Renders the control with the ids its label, helper and error need. */
  children: (ids: { id: string; describedBy: string | undefined }) => ReactNode;
  counter?: { length: number; limit: number };
}

/** The counter appears once an answer passes 80% of its limit, so it never nags early. */
const COUNTER_FROM = 0.8;

export function Field({ label, helper, error, children, counter }: FieldProps) {
  const id = useId();
  const helperId = `${id}-helper`;
  const errorId = `${id}-error`;
  const describedBy = [helper ? helperId : null, error ? errorId : null].filter(Boolean).join(" ");
  const showCounter = counter && counter.length > counter.limit * COUNTER_FROM;
  return (
    <div className="ap-field">
      <label className="ap-field__label" htmlFor={id}>
        {label}
      </label>
      {helper && (
        <p className="ap-field__helper" id={helperId}>
          {helper}
        </p>
      )}
      {children({ id, describedBy: describedBy || undefined })}
      {(error || showCounter) && (
        <div className="ap-field__foot">
          {error && <FieldError id={errorId} message={error} />}
          {showCounter && (
            <span className="ap-field__counter mono" aria-live="polite">
              {counter.length} / {counter.limit}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function FieldError({ id, message }: { id?: string; message: string }) {
  return (
    <p className="ap-field__error" id={id}>
      <CircleAlert size={14} strokeWidth={1.5} aria-hidden="true" />
      {message}
    </p>
  );
}

interface TextAreaProps {
  id: string;
  describedBy: string | undefined;
  value: string;
  limit: number;
  invalid: boolean;
  onChange: (value: string) => void;
}

/** Starts at three lines and grows with the answer, so nothing scrolls inside the box. */
export function TextArea({ id, describedBy, value, limit, invalid, onChange }: TextAreaProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight + 2}px`;
  }, [value]);
  return (
    <textarea
      ref={ref}
      id={id}
      className="input ap-textarea"
      rows={3}
      value={value}
      maxLength={limit}
      aria-describedby={describedBy}
      aria-invalid={invalid || undefined}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

interface ChoiceChipsProps<T extends string> {
  label: string;
  choices: Pick<Choice<T>, "value" | "label">[];
  selected: T[];
  onToggle: (value: T) => void;
  /** "segmented" sits as one joined pill with a sliding indicator (time on the idea); chips wrap freely. */
  look?: "chips" | "segmented";
}

/**
 * Toggle buttons: the caller decides whether a press replaces the choice or adds to it. Pressing the chosen
 * one again takes it back, which a radio group could not do.
 */
export function ChoiceChips<T extends string>({
  label,
  choices,
  selected,
  onToggle,
  look = "chips",
}: ChoiceChipsProps<T>) {
  if (look === "segmented") {
    return (
      <JoinedChoices label={label} choices={choices} selected={selected} onToggle={onToggle} />
    );
  }
  return (
    <div className="ap-chips" role="group" aria-label={label}>
      {choices.map((choice) => {
        const on = selected.includes(choice.value);
        return (
          <button
            key={choice.value}
            type="button"
            className="chip-btn ap-chip"
            aria-pressed={on}
            onClick={() => onToggle(choice.value)}
          >
            {on && <Check size={13} strokeWidth={2} aria-hidden="true" />}
            {choice.label}
          </button>
        );
      })}
    </div>
  );
}

function JoinedChoices<T extends string>({
  label,
  choices,
  selected,
  onToggle,
}: Omit<ChoiceChipsProps<T>, "look">) {
  const itemsKey = choices.map((c) => `${c.value}:${c.label}`).join("|");
  const { rootRef, indRef } = useSlidingIndicator<HTMLDivElement>(selected[0], itemsKey);
  return (
    <div ref={rootRef} className="seg seg--block ap-joined" role="group" aria-label={label}>
      <span className="seg__ind" ref={indRef} aria-hidden="true" />
      {choices.map((choice) => {
        const on = selected.includes(choice.value);
        return (
          <button
            key={choice.value}
            type="button"
            className="seg__btn"
            data-selected={on}
            aria-pressed={on}
            onClick={() => onToggle(choice.value)}
          >
            {choice.label}
          </button>
        );
      })}
    </div>
  );
}
