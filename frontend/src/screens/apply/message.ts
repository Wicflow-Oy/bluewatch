// A message the student page shows about a problem: ours, or the server's.
import { useT } from "../../i18n/messages";
import { applyMessages } from "./messages";

type ErrorKey =
  | "titleShort"
  | "problemOrSolution"
  | "fullAddress"
  | "unreachable"
  | "tooLong"
  | "rateLimited"
  | "consentChanged"
  | "serverFailed";

/**
 * One of our messages, worded when it is shown (so a language switch rewords it on screen), or the
 * server's own words, which arrive in the language the request asked for.
 */
export type Message = { key: ErrorKey } | { text: string };

export const own = (key: ErrorKey): Message => ({ key });

/** Words a Message in the current language. */
export function useMessageText(): (message: Message) => string {
  const { t } = useT(applyMessages);
  return (message) => ("key" in message ? t(`error_${message.key}`) : message.text);
}
