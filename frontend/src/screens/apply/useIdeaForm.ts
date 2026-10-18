import { useCallback, useEffect, useState } from "react";
import { useLang } from "../../i18n/lang";
import { ideasApi } from "../ideas/api";
import type { IdeaForm, PresetName } from "../ideas/types";

interface Loaded {
  key: string;
  /** The last form that loaded; kept while a reload runs, so the page never blanks. */
  form: IdeaForm | null;
  failed: boolean;
}

/**
 * /api/ideas/form for the preset and language, with a reload for Retry and for a changed consent text.
 * A language switch keeps the last form on screen until the new labels arrive.
 */
export function useIdeaForm(preset: PresetName) {
  const lang = useLang();
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState<Loaded>({ key: "", form: null, failed: false });
  const key = `${preset}/${lang}/${attempt}`;

  useEffect(() => {
    let current = true;
    ideasApi.form(preset).then(
      (form) => current && setLoaded({ key, form, failed: false }),
      () => current && setLoaded((last) => ({ key, form: last.form, failed: true })),
    );
    return () => {
      current = false;
    };
  }, [key, preset]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  const form = loaded.form?.preset === preset ? loaded.form : null;
  return { form, failed: form === null && loaded.key === key && loaded.failed, reload };
}
