// "Invite via organiser" for a public lead: a message to an organisation, never to a person, that the
// reviewer copies and sends from their own e-mail.
import { Copy, ExternalLink, Send } from "lucide-react";
import { useRef } from "react";
import { useT } from "../../i18n/messages";
import { Chip } from "../../ui/Chip";
import { useToast } from "../../ui/Toast";
import { ideasMessages } from "./messages";
import type { Invite } from "./types";

const ROUTE_KINDS = ["organiser", "university_office"] as const;

/** Our word for a known route kind; an unknown one shows as the API sent it. */
function useRouteKind(kind: string): string {
  const { t } = useT(ideasMessages);
  const known = ROUTE_KINDS.find((k) => k === kind);
  return known ? t(`routeKind_${known}`) : kind;
}

export function InvitePanel({ invite }: { invite: Invite }) {
  const { t } = useT(ideasMessages);
  const toast = useToast();
  const box = useRef<HTMLTextAreaElement>(null);
  const { route } = invite;
  const routeKind = useRouteKind(route.kind);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(invite.message);
      toast(t("copied"), "success");
    } catch {
      // No clipboard (an insecure origin or a blocked permission): select it for the keyboard instead.
      box.current?.select();
      toast(t("copyBlocked"));
    }
  };

  return (
    <section className="ih-box" aria-labelledby="ih-invite-title">
      <h3 className="ih-box__title" id="ih-invite-title">
        <span className="ih-invite__title">
          <Send size={14} strokeWidth={1.75} aria-hidden="true" />
          {t("inviteTitle")}
        </span>
      </h3>
      <div className="ih-invite__route">
        <p className="ih-invite__org">
          {route.organisation}
          <Chip tone="grey">{routeKind}</Chip>
        </p>
        <p className="ih-invite__how">{route.how}</p>
        {route.contact_page_url && (
          <a
            className="ih-link"
            href={route.contact_page_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <ExternalLink size={12} strokeWidth={1.5} aria-hidden="true" />
            {t("contactPage")}
          </a>
        )}
      </div>
      {/* The message keeps the language it was drafted in: it goes to the organisation as written. */}
      <textarea
        ref={box}
        className="input ih-invite__message mono"
        readOnly
        rows={6}
        value={invite.message}
        aria-label={t("inviteMessage")}
      />
      <div>
        <button type="button" className="btn" onClick={copy}>
          <Copy aria-hidden="true" />
          {t("copyMessage")}
        </button>
      </div>
      {/* The API's note is written for a demo audience; this is the same fact as a product setting. */}
      <p className="ih-caption">{t("sendingOff")}</p>
      <p className="ih-caption">{t("organisationsOnly")}</p>
    </section>
  );
}
