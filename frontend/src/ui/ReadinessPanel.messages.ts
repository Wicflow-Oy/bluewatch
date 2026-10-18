import { defineMessages } from "../i18n/messages";

export const readinessPanelMessages = defineMessages({
  en: {
    readinessLevels: "Readiness levels",
    levelOf: "Level {level} of {max}",
    raiseWith: "Raise it with: {how}.",
    unknownBecause: "Unknown: {reason}.",
    noImpactArea: "No impact area found yet",
    areasInferred:
      "Ocean Impact Navigator areas. Inferred from what the company does, not from an impact claim.",
    ownWords: "Company's own words:",
    draftScale: "Our own draft scale. Not calibrated: no reference keys exist (n = 0).",
  },
  fi: {
    readinessLevels: "Valmiustasot",
    levelOf: "Taso {level}/{max}",
    raiseWith: "Tasoa nostaa: {how}.",
    unknownBecause: "Ei tiedossa: {reason}.",
    noImpactArea: "Vaikuttavuusaluetta ei ole vielä löytynyt",
    areasInferred:
      "Ocean Impact Navigator -alueet. Päätelty yrityksen toiminnasta, ei vaikuttavuusväitteestä.",
    ownWords: "Yrityksen omin sanoin:",
    draftScale: "Oma luonnosasteikkomme. Ei kalibroitu: vertailuluokituksia ei ole (n = 0).",
  },
  sv: {
    readinessLevels: "Mognadsnivåer",
    levelOf: "Nivå {level} av {max}",
    raiseWith: "Höjs genom: {how}.",
    unknownBecause: "Okänt: {reason}.",
    noImpactArea: "Inget påverkansområde hittat än",
    areasInferred:
      "Områden enligt Ocean Impact Navigator. Härledda från vad bolaget gör, inte från ett påstående om påverkan.",
    ownWords: "Med bolagets egna ord:",
    draftScale: "Vår egen utkastskala. Inte kalibrerad: det finns inget facit (n = 0).",
  },
});
