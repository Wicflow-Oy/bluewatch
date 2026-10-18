import { Fragment, type ReactNode } from "react";

/**
 * A translated sentence with parts that need their own markup (a link, a mono figure). The message
 * keeps its language's word order, and each {name} placeholder becomes the node given for it.
 */
export function withSlots(text: string, slots: Record<string, ReactNode>): ReactNode {
  return text.split(/(\{\w+\})/).map((part, i) => {
    const name = /^\{(\w+)\}$/.exec(part)?.[1];
    return <Fragment key={i}>{name !== undefined && name in slots ? slots[name] : part}</Fragment>;
  });
}

/** For tn(): keeps {n} in the text, so withSlots can put the figure in its own markup. */
export const FIGURE_SLOT = { n: "{n}" };
