import { useEffect, useState } from "react";
import { ApiError } from "../../api";
import { useT } from "../../i18n/messages";
import { useToast } from "../../ui/Toast";
import { ideasApi } from "../ideas/api";
import type { IdeaSubmission, SessionShares } from "../ideas/types";
import { explain, outcomeMessage } from "./errors";
import type { Message } from "./message";
import { applyMessages } from "./messages";
import type { Shared, ShareBusy } from "./SharePanel";

/**
 * Consent, sharing and withdrawing for the read on screen. Nothing is shared until the team ticks the
 * box; a changed consent text on the server asks for the tick again. An idea this browser session shared
 * before the page was opened again (a reload, a visit elsewhere) is asked from the server, so Withdraw is
 * always within reach.
 */
export function useSharing(aiRead: boolean, reloadForm: () => void) {
  const { tn } = useT(applyMessages);
  const toast = useToast();
  const [consent, setConsent] = useState(false);
  const [shared, setShared] = useState<Shared | null>(null);
  const [busy, setBusy] = useState<ShareBusy>(null);
  const [error, setError] = useState<Message | null>(null);
  const [earlier, setEarlier] = useState<SessionShares | null>(null);

  useEffect(() => {
    let current = true;
    ideasApi
      .shared()
      .then((found) => current && setEarlier(found.count > 0 ? found : null))
      // Without an answer the page works as before: a new share shows its own receipt and Withdraw.
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, []);

  /** A new read starts with the box unticked and no old error. */
  function reset() {
    setConsent(false);
    setError(null);
  }

  async function share(submission: IdeaSubmission, consentVersion: string) {
    setBusy("share");
    setError(null);
    try {
      const receipt = await ideasApi.share(submission, aiRead, consentVersion);
      setShared({ receipt, submission });
      setEarlier(null);
      setConsent(false);
    } catch (failure) {
      setError(outcomeMessage(explain(failure)));
      if (failure instanceof ApiError && failure.status === 409) {
        setConsent(false);
        reloadForm();
      }
    } finally {
      setBusy(null);
    }
  }

  async function withdraw() {
    setBusy("withdraw");
    setError(null);
    try {
      const { removed, message } = await ideasApi.withdraw();
      setShared(null);
      setEarlier(null);
      setConsent(false);
      // The API counts "idea(s)"; the team reads a sentence about its own idea.
      toast(removed > 0 ? tn("withdrawn", removed) : message, "success");
    } catch (failure) {
      setError(outcomeMessage(explain(failure)));
    } finally {
      setBusy(null);
    }
  }

  return { consent, setConsent, shared, earlier, busy, error, reset, share, withdraw };
}
