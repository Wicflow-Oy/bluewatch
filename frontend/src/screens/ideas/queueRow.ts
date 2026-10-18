// What the table rows and the stacked cards share, and the row-to-card morph both ways.
import type { MouseEvent } from "react";
import { listRow, morph, sheetPanel } from "../../lib/motion";
import { navigateNow } from "../../lib/router";
import type { QueueItem } from "./types";

/** What a row or card needs besides its item. */
export interface RowContext {
  /** The higher-ranked item this one reads like, if any. */
  duplicateOf: (item: QueueItem) => QueueItem | undefined;
  selectedId: string | null;
  /** Every item is invented sample data, and each one says so. */
  sample: boolean;
  today: string;
  rowRef: (id: string) => (el: HTMLElement | null) => void;
}

const CARD = "bw-card";

/** The row grows into the idea card (a fade where View Transitions or motion are unavailable). */
export function openItem(item: QueueItem) {
  morph(CARD, listRow(item.id), () => navigateNow({ name: "ideas", itemId: item.id }), sheetPanel);
}

/** The card shrinks back into its row. */
export function closeItem(itemId: string | undefined) {
  morph(
    CARD,
    sheetPanel(),
    () => navigateNow({ name: "ideas" }),
    () => (itemId ? listRow(itemId) : null),
  );
}

/**
 * A plain click on a link to a card opens it with the morph; a middle click or a modifier keeps the
 * browser's own behaviour (a new tab).
 */
export function onCardLink(e: MouseEvent<HTMLAnchorElement>, item: QueueItem) {
  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  e.preventDefault();
  openItem(item);
}
