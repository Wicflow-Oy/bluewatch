// One evidence request through the desk's state machine: draft, approve, send, simulated reply.
// The server owns every rule (the hash, the policy, the transitions); this hook only walks the steps
// and keeps what each answer said.
import { useCallback, useEffect, useState } from "react";
import type { DraftLanguage, Mode } from "../../api";
import type { DeskDraft, DeskReply } from "../../contracts";
import { desk, type Outcome } from "../../data";

export type DeskStep = "approve" | "send" | "reply";

export interface ReadyDesk {
  kind: "ready";
  view: DeskDraft;
  reply: DeskReply | null;
  busy: DeskStep | null;
  /** The last step didn't go through; `detail` is the desk's own reason when it gave one. */
  failure: { detail: string | null } | null;
}

export type DeskState =
  | { kind: "creating" }
  | ReadyDesk
  | { kind: "refused"; message: string }
  | { kind: "unavailable" }
  | { kind: "failed" };

interface Keyed {
  key: string;
  state: DeskState;
}

export interface DeskControls {
  state: DeskState;
  approve(): void;
  send(): void;
  reply(): void;
  /** A fresh desk and a new draft for the same company, bridge and language. */
  startOver(): void;
}

const CREATING: DeskState = { kind: "creating" };

/** What the draft is for. */
export interface DeskSubject {
  companyId: string;
  /** The bridge the draft is about; without it, the company's best bridge or opportunity. */
  bridgeId?: string;
  mode: Mode;
  language: DraftLanguage;
}

export function useDesk(
  { companyId, bridgeId, mode, language }: DeskSubject,
  enabled: boolean,
  onSent: () => void,
): DeskControls {
  const [round, setRound] = useState(0);
  const [restarting, setRestarting] = useState(false);
  const key = `${companyId}|${bridgeId ?? ""}|${mode}|${language}|${round}`;
  const [current, setCurrent] = useState<Keyed | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let live = true;
    const settle = (state: DeskState) => live && setCurrent({ key, state });
    desk.create(companyId, mode, language, bridgeId).then(
      (out) => settle(fromCreate(out)),
      () => settle({ kind: "failed" }),
    );
    return () => {
      live = false;
    };
  }, [companyId, bridgeId, mode, language, enabled, key]);

  // A state from an earlier company, bridge, language or round is stale: the new draft is still on its way.
  const state = current?.key === key && !restarting ? current.state : CREATING;

  const patch = useCallback(
    (at: string, update: (desk: ReadyDesk) => ReadyDesk) =>
      setCurrent((prev) =>
        prev && prev.key === at && prev.state.kind === "ready"
          ? { key: at, state: update(prev.state) }
          : prev,
      ),
    [],
  );

  const run = useCallback(
    async <T>(
      step: DeskStep,
      call: (view: DeskDraft) => Promise<Outcome<T>>,
      apply: (desk: ReadyDesk, data: T) => ReadyDesk,
    ) => {
      if (state.kind !== "ready" || state.busy) return;
      const at = key;
      const draftId = state.view.draft.id;
      patch(at, (d) => ({ ...d, busy: step, failure: null }));
      // A thrown error is shown like a refusal: the step didn't happen and nothing was sent.
      const out = await call(state.view).catch(() => null);
      if (out?.kind === "result") {
        patch(at, (d) => ({ ...apply(d, out.data), busy: null }));
        if (step === "send") onSent();
        return;
      }
      // Re-read the draft so the audit trail shows the refusal the desk wrote down.
      const fresh = await desk.draft(draftId).catch(() => null);
      patch(at, (d) => ({
        ...d,
        view: fresh?.kind === "result" ? fresh.data : d.view,
        busy: null,
        failure: { detail: out?.kind === "rejected" ? out.message : null },
      }));
    },
    [state, key, patch, onSent],
  );

  const approve = useCallback(
    () =>
      run(
        "approve",
        (view) => desk.approve(view.draft.id, view.text_hash),
        (d, view) => ({ ...d, view }),
      ),
    [run],
  );

  const send = useCallback(
    () =>
      run(
        "send",
        (view) => desk.send(view.draft.id),
        (d, view) => ({ ...d, view }),
      ),
    [run],
  );

  const reply = useCallback(
    () =>
      run(
        "reply",
        (view) => desk.reply(view.draft.id),
        (d, data) => ({ ...d, view: data.draft, reply: data }),
      ),
    [run],
  );

  const startOver = useCallback(async () => {
    setRestarting(true);
    // Clearing the visitor's old drafts keeps the trail to this run; a new draft follows either way.
    await desk.reset().catch(() => null);
    setRestarting(false);
    setRound((r) => r + 1);
  }, []);

  return { state, approve, send, reply, startOver };
}

function fromCreate(out: Outcome<DeskDraft>): DeskState {
  switch (out.kind) {
    case "result":
      return { kind: "ready", view: out.data, reply: null, busy: null, failure: null };
    case "rejected":
      return { kind: "refused", message: out.message };
    case "unavailable":
      return { kind: "unavailable" };
  }
}
