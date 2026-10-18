// Up to three public links. Nothing opens them automatically: a person at A'Pelago does.
import { Plus } from "lucide-react";
import { useState } from "react";
import { useT } from "../../i18n/messages";
import { isFullAddress } from "./draft";
import { FieldError } from "./fields";
import { own, useMessageText, type Message } from "./message";
import { applyMessages } from "./messages";

interface LinkFieldsProps {
  links: string[];
  max: number;
  limit: number;
  error: Message | undefined;
  onChange: (links: string[]) => void;
}

export function LinkFields({ links, max, limit, error, onChange }: LinkFieldsProps) {
  const { t } = useT(applyMessages);
  const say = useMessageText();
  // Only links the visitor has left are checked, so a half-typed address is never called wrong.
  const [left, setLeft] = useState<number[]>([]);
  const invalid = (index: number) =>
    left.includes(index) && links[index].trim() !== "" && !isFullAddress(links[index]);
  const shownError = links.some((_, i) => invalid(i)) ? own("fullAddress") : error;
  return (
    <div className="ap-field">
      <span className="ap-field__label" id="ap-links-label">
        {t("links")}
      </span>
      <p className="ap-field__helper" id="ap-links-helper">
        {t("linksHelper")}
      </p>
      <div className="ap-links">
        {links.map((link, index) => (
          <input
            key={index}
            type="url"
            inputMode="url"
            autoComplete="url"
            className="input"
            value={link}
            maxLength={limit}
            aria-labelledby="ap-links-label"
            aria-describedby="ap-links-helper"
            aria-invalid={invalid(index) || undefined}
            onChange={(e) => onChange(links.map((l, i) => (i === index ? e.target.value : l)))}
            onBlur={() => setLeft((l) => (l.includes(index) ? l : [...l, index]))}
          />
        ))}
      </div>
      {shownError && <FieldError message={say(shownError)} />}
      {links.length < max && (
        <button
          type="button"
          className="btn btn--subtle btn--sm ap-add"
          onClick={() => onChange([...links, ""])}
        >
          <Plus size={16} strokeWidth={1.5} aria-hidden="true" />
          {t("addLink")}
        </button>
      )}
    </div>
  );
}
