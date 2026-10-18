// A business-ID field: the country, a format hint and a format check before anything is sent, so a
// mistyped ID never leaves the browser. The register (through our API) still checks the check digit.
import { LoaderCircle, Search } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import type { Country } from "../api";
import { useT } from "../i18n/messages";
import { countryName } from "../lib/labels";
import { idInputMessages } from "./IdInput.messages";
import { useSlidingIndicator } from "./useSlidingIndicator";
import "./Segmented.css";
import "./IdInput.css";

const COUNTRIES: Country[] = ["FI", "NO", "EE"];

const PLACEHOLDER: Record<Country, string> = {
  FI: "1234567-8",
  NO: "123 456 789",
  EE: "12345678",
};

const FORMAT: Record<Country, RegExp> = {
  FI: /^\d{7}-?\d$/,
  NO: /^\d{9}$/,
  EE: /^\d{8}$/,
};

function isBusinessIdFormat(country: Country, value: string): boolean {
  return FORMAT[country].test(value.replace(/\s/g, ""));
}

interface IdInputProps {
  country: Country;
  value: string;
  onCountry(country: Country): void;
  onChange(value: string): void;
  /** Called only when the value has the country's format. */
  onSubmit(): void;
  busy: boolean;
  /** A refusal from the API (a wrong check digit, a rate limit), shown in place of the hint. */
  error?: string | null;
}

export function IdInput({
  country,
  value,
  onCountry,
  onChange,
  onSubmit,
  busy,
  error,
}: IdInputProps) {
  const id = useId();
  const { t } = useT(idInputMessages);
  const [formatFailed, setFormatFailed] = useState(false);
  const hint = t(`hint_${country}`);
  const message = formatFailed ? hint : (error ?? hint);
  const invalid = formatFailed || Boolean(error);
  const { rootRef, indRef } = useSlidingIndicator<HTMLFieldSetElement>(country);

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (busy) return;
    if (!isBusinessIdFormat(country, value)) {
      setFormatFailed(true);
      return;
    }
    onSubmit();
  };

  return (
    <form className="id-input" onSubmit={submit} noValidate autoComplete="off" aria-busy={busy}>
      <fieldset className="id-input__countries seg" ref={rootRef}>
        <legend className="sr-only">{t("country")}</legend>
        <span className="seg__ind" ref={indRef} aria-hidden="true" />
        {COUNTRIES.map((c) => (
          <label key={c} className="id-input__country seg__btn" data-selected={c === country}>
            <input
              type="radio"
              name={`${id}-country`}
              value={c}
              checked={c === country}
              onChange={() => {
                setFormatFailed(false);
                onCountry(c);
              }}
            />
            <span>{countryName(c)}</span>
          </label>
        ))}
      </fieldset>
      <label className="id-input__label" htmlFor={`${id}-value`}>
        {t("businessId")}
      </label>
      <div className="id-input__row">
        <input
          id={`${id}-value`}
          className="input mono id-input__field"
          value={value}
          onChange={(e) => {
            setFormatFailed(false);
            onChange(e.target.value);
          }}
          placeholder={PLACEHOLDER[country]}
          inputMode={country === "FI" ? "text" : "numeric"}
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          aria-invalid={invalid}
          aria-describedby={`${id}-help`}
        />
        <button type="submit" className="btn btn--primary id-input__submit">
          {busy ? (
            <LoaderCircle className="spin" size={16} strokeWidth={1.5} aria-hidden="true" />
          ) : (
            <Search size={16} strokeWidth={1.5} aria-hidden="true" />
          )}
          {t("lookUp")}
        </button>
      </div>
      <p
        id={`${id}-help`}
        className={`id-input__help${invalid ? " id-input__help--error" : ""}`}
        aria-live="polite"
      >
        {message}
      </p>
    </form>
  );
}
