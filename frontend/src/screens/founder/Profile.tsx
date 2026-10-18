// The register's profile of the company: the only facts Founder view states, each from the register.
import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import type { LookupResult } from "../../api";
import type { FounderProfile } from "../../contracts";
import { useT } from "../../i18n/messages";
import { formatDay, formatStamp, humanText, registryLabel } from "../../lib/format";
import { href } from "../../lib/router";
import { Chip } from "../../ui/Chip";
import { Panel } from "../../ui/Panel";
import { SourceStatusPill } from "../../ui/SourceStatusPill";
import { founderMessages } from "./messages";

interface ProfileProps {
  profile: FounderProfile;
  lookup: LookupResult;
  /** The answer came from the recorded data because the API could not be reached. */
  recorded: boolean;
}

export function Profile({ profile, lookup, recorded }: ProfileProps) {
  const { t } = useT(founderMessages);
  const registry = lookup.registry;
  const name = profile.name ?? registry?.name ?? registryLabel(lookup.country, lookup.business_id);
  const founded = registry?.founded ?? profile.founded;
  const industry = registry?.industry_code
    ? [registry.industry_scheme, registry.industry_code].filter(Boolean).join(" ")
    : null;
  const checkedAt = lookup.status.checked_at;

  return (
    <Panel className="founder-profile">
      <div className="founder-profile__top">
        <div className="founder-profile__title">
          <h2 className="founder-profile__name t-h2">{name}</h2>
          {lookup.company_id && (
            <a
              className="founder-profile__card"
              href={href({ name: "card", companyId: lookup.company_id })}
            >
              {t("openCard")}
              <ArrowUpRight size={14} strokeWidth={1.5} aria-hidden="true" />
            </a>
          )}
        </div>
        <div className="founder-profile__source">
          {recorded && checkedAt && (
            <Chip tone="grey">{t("recordedAt", { stamp: formatStamp(checkedAt) })}</Chip>
          )}
          <SourceStatusPill status={lookup.status} />
        </div>
      </div>
      <dl className="founder-facts">
        <Fact label={t("fact_businessId")}>
          <span className="mono">{registryLabel(lookup.country, lookup.business_id)}</span>
        </Fact>
        <Fact label={t("fact_form")}>{registry?.form ?? <Unknown />}</Fact>
        <Fact label={t("fact_founded")}>
          {founded ? (
            <span className="mono">{formatDay(founded, { year: true })}</span>
          ) : (
            <Unknown />
          )}
        </Fact>
        <Fact label={t("fact_municipality")}>{registry?.municipality ?? <Unknown />}</Fact>
        <Fact label={t("fact_industry")}>
          {industry ? <span className="mono">{industry}</span> : <Unknown />}
        </Fact>
      </dl>
      <Themes themes={profile.themes ?? []} />
    </Panel>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="founder-fact">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Unknown() {
  const { t } = useT(founderMessages);
  return (
    <Chip tone="hatch" wrap title={t("unknownWhy")}>
      {t("unknown")}
    </Chip>
  );
}

/** The backend's industry themes (bluewatch/founder/view.py INDUSTRY_THEMES), as message keys. */
const THEME_KEYS = {
  "fish processing": "theme_fishProcessing",
  shipbuilding: "theme_shipbuilding",
  "ship repair": "theme_shipRepair",
  "port and water transport services": "theme_portServices",
  "fishing and aquaculture": "theme_fishing",
  "water transport": "theme_waterTransport",
  "water supply": "theme_waterSupply",
  wastewater: "theme_wastewater",
  software: "theme_software",
  "engineering and technical consultancy": "theme_engineering",
  "research and development": "theme_research",
} as const;

function isThemeKey(theme: string): theme is keyof typeof THEME_KEYS {
  return Object.hasOwn(THEME_KEYS, theme);
}

function Themes({ themes }: { themes: string[] }) {
  const { t } = useT(founderMessages);
  const label = (theme: string) => (isThemeKey(theme) ? t(THEME_KEYS[theme]) : humanText(theme));
  return (
    <div className="founder-themes">
      <span className="founder-themes__label">{t("themesLabel")}</span>
      {themes.length > 0 ? (
        <ul className="founder-themes__list">
          {themes.map((theme) => (
            <li key={theme}>
              <Chip>{label(theme)}</Chip>
            </li>
          ))}
        </ul>
      ) : (
        <Chip tone="hatch" wrap>
          {t("themesUnknown")}
        </Chip>
      )}
    </div>
  );
}
