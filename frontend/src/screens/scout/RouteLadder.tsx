// The ways to reach a team, best first, all through organisations; the rung the draft is written for is
// marked. Contact pages are organisation pages: the plan builder never keeps a personal one.
import { ArrowUpRight } from "lucide-react";
import type { Route } from "../../contracts";
import { useT } from "../../i18n/messages";
import { hostOf, humanText } from "../../lib/format";
import { Chip } from "../../ui/Chip";
import { scoutMessages } from "./messages";

interface RouteLadderProps {
  routes: Route[];
  draftRank?: number;
}

export function RouteLadder({ routes, draftRank }: RouteLadderProps) {
  const { t } = useT(scoutMessages);
  return (
    <>
      <ol className="scout-routes">
        {routes.map((route) => (
          <Rung key={route.rank} route={route} isDraftTarget={route.rank === draftRank} />
        ))}
      </ol>
      <p className="scout-detail__note">
        {t("routeNoteOrganisations")} {t("routeNoteOptIn")}
      </p>
    </>
  );
}

function Rung({ route, isDraftTarget }: { route: Route; isDraftTarget: boolean }) {
  const { t } = useT(scoutMessages);
  return (
    <li className={`scout-route${isDraftTarget ? " scout-route--target" : ""}`}>
      <span className="scout-route__rank mono" aria-hidden="true">
        {route.rank}
      </span>
      <div className="scout-route__body">
        <div className="scout-route__head">
          <span className="scout-route__org">{route.organisation}</span>
          <Chip wrap>{t(`route_${route.kind}`)}</Chip>
          {isDraftTarget && (
            <Chip tone="accent" wrap>
              {t("draftGoesHere")}
            </Chip>
          )}
        </div>
        <p className="scout-route__how">{humanText(route.how)}</p>
        {route.contact_page_url && (
          <a
            className="scout-route__link chip-btn"
            href={route.contact_page_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {hostOf(route.contact_page_url) ?? t("contactPage")}
            <ArrowUpRight size={12} strokeWidth={1.75} aria-hidden="true" />
            <span className="sr-only"> {t("opensNewTab")}</span>
          </a>
        )}
      </div>
    </li>
  );
}
