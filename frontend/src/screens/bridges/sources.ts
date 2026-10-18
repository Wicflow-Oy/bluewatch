// Bridge evidence carries a short tag instead of a source family; these say who said it, in words.
import type { BridgeEvidence } from "../../contracts";
import { translator } from "../../i18n/messages";
import { hostOf } from "../../lib/format";
import { evidenceSourceLabel } from "../../lib/labels";
import type { SourceRef } from "../../ui/SourceChip";
import { bridgesMessages } from "./messages";

const REGISTER_FAMILY: Record<string, string> = { FI: "prh", NO: "brreg", EE: "rik" };

/** "cordis_json_2026-10-17" is the CORDIS file of that day: the family is the part before "_json". */
function familyOf(tag: string, country: string | null | undefined): string {
  if (tag === "registry") return REGISTER_FAMILY[country ?? ""] ?? "registry";
  if (tag === "dossier") return "research_pack";
  return tag.split("_json")[0];
}

/** `hidden`: the host would name the company, so it is left out. */
function labelOf(evidence: BridgeEvidence, country: string | null | undefined, hidden: boolean) {
  const { t } = translator(bridgesMessages);
  const host = hidden ? null : hostOf(evidence.url);
  switch (evidence.tag) {
    case "site":
      return host ? evidenceSourceLabel({ source_family: `site:${host}` }) : t("companySite");
    case "read":
      return host ? t("pageReadAt", { host }) : t("pageRead");
    case "snippet":
      return t("searchSnippet");
    case "registry":
      if (!REGISTER_FAMILY[country ?? ""]) return t("companyRegister");
      break;
    case "ted":
      // The award notice names the winner, so with names hidden it is only described.
      if (hidden) return t("tedAwardNotice");
      break;
  }
  return evidenceSourceLabel({ source_family: familyOf(evidence.tag, country) });
}

/**
 * The chip for one piece of bridge evidence. `hidden` is the company side with names hidden: no link and no
 * host, because both would name the company.
 */
export function bridgeSource(
  evidence: BridgeEvidence,
  country: string | null | undefined,
  hidden = false,
): SourceRef {
  return {
    label: labelOf(evidence, country, hidden) ?? translator(bridgesMessages).t("sourceNotNamed"),
    url: hidden ? null : evidence.url,
    event: evidence.date,
    deadline: evidence.deadline,
  };
}
