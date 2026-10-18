// A translated sentence with React nodes in its {placeholders}, so a figure can sit in mono or a word
// can carry a style without cutting the sentence into fragments that each language orders differently.
import { Fragment, type ReactNode } from "react";

interface RichProps {
  /** The message as written, placeholders unfilled: t("key") without params. */
  text: string;
  values: Record<string, ReactNode>;
}

export function Rich({ text, values }: RichProps) {
  // split() with a capture group alternates text and placeholder names: odd indexes are names.
  return text
    .split(/\{(\w+)\}/)
    .map((part, i) => (i % 2 === 0 ? part : <Fragment key={i}>{values[part]}</Fragment>));
}

/** A count or a range in the figures face. */
export function Figure({ children }: { children: ReactNode }) {
  return <span className="mono">{children}</span>;
}
