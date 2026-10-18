// The ranked list: a table on a desktop, stacked cards below it. J and K move the selection and
// Enter opens it, as on the other lists (SCREENS.md §2.8).
import { useEffect, useRef, useState } from "react";
import { QueueCards } from "./QueueCards";
import { openItem, type RowContext } from "./queueRow";
import { QueueTable } from "./QueueTable";
import type { IdeaQueue, QueueItem } from "./types";

interface QueueListProps {
  queue: IdeaQueue;
  items: QueueItem[];
  stacked: boolean;
  today: string;
  /** Every item is invented sample data, and each one says so. */
  sample: boolean;
  /** Off while a drawer is open, so J and K don't move rows behind it. */
  keyboard: boolean;
}

export function QueueList({ queue, items, stacked, today, sample, keyboard }: QueueListProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const rows = useRef(new Map<string, HTMLElement>());

  useEffect(() => {
    if (!keyboard) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const target = e.target instanceof HTMLElement ? e.target : null;
      if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
      const index = items.findIndex((item) => item.id === selectedId);
      if (e.key === "Enter") {
        // A focused link or button already answers Enter itself.
        if (index >= 0 && !target?.closest("a, button")) openItem(items[index]);
        return;
      }
      const step = e.key === "j" ? 1 : e.key === "k" ? -1 : 0;
      if (step === 0 || items.length === 0) return;
      const next = items[Math.min(items.length - 1, Math.max(0, index + step))];
      setSelectedId(next.id);
      rows.current.get(next.id)?.scrollIntoView({ block: "nearest" });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [keyboard, items, selectedId]);

  const byId = new Map(queue.items.map((item) => [item.id, item]));
  const context: RowContext = {
    duplicateOf: (item) => (item.duplicate_of ? byId.get(item.duplicate_of) : undefined),
    selectedId,
    sample,
    today,
    rowRef: (id) => (el) => {
      if (el) rows.current.set(id, el);
      else rows.current.delete(id);
    },
  };

  return stacked ? (
    <QueueCards items={items} context={context} />
  ) : (
    <QueueTable items={items} topN={queue.top_n} context={context} />
  );
}
