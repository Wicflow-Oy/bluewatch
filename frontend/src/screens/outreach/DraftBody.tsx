// The message text exactly as it would be sent. It is plain text: the legal footer after the "----"
// rule is set smaller so the request itself reads first, and nothing else is restyled.
import { useT } from "../../i18n/messages";
import { outreachMessages } from "./messages";

const FOOTER_RULE = "\n----\n";

export function DraftBody({ body }: { body: string }) {
  const { t } = useT(outreachMessages);
  const at = body.indexOf(FOOTER_RULE);
  const main = at === -1 ? body : body.slice(0, at);
  const footer = at === -1 ? null : body.slice(at + FOOTER_RULE.length);
  return (
    <div className="outreach-body inset" tabIndex={0} role="region" aria-label={t("messageText")}>
      <p className="outreach-body__text">{main}</p>
      {footer && <p className="outreach-body__footer">{footer}</p>}
    </div>
  );
}
