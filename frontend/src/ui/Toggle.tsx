import "./Toggle.css";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  hint?: string;
  /** md: 40 x 24 (default), lg: 52 x 32 (the mockup's switch). */
  size?: "md" | "lg";
}

export function Toggle({ checked, onChange, label, hint, size = "md" }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      className={`toggle toggle--${size}`}
      onClick={() => onChange(!checked)}
      title={hint}
    >
      <span className="toggle__track" aria-hidden="true">
        <span className="toggle__thumb" />
      </span>
      <span className="toggle__label">{label}</span>
    </button>
  );
}
