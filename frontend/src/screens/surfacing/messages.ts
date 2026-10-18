// Words on the Surfacing page: the header, the "Why these" popover, the toolbar, the rows, the rail and the foot.
// The list's name and the API's prose (reasons, next steps, why these) arrive translated from the API.
import { defineMessages } from "../../i18n/messages";

export const surfacingMessages = defineMessages({
  en: {
    explainer_apelago:
      "New ocean companies worth inviting to a programme, each with the reason and the next step. Up to 10, never padded.",
    explainer_redstone:
      "New ocean companies worth a first call, each with the reason and the next step. Up to 10, never padded.",
    explainer_climate_apelago:
      "New climate and circular-economy companies worth inviting to a programme, each with the reason and the next step. Up to 10, never padded.",
    explainer_climate_redstone:
      "New climate and circular-economy companies worth a first call, each with the reason and the next step. Up to 10, never padded.",
    listFailedTitle: "The list couldn't load",
    listFailedBody: "Search ({keys}), Founder view and Precision still work.",
    retry: "Retry",
    loading: "Loading {list}",

    week: "Week {n}",
    since: "since {when}",
    countSpoken_one: "{count} on the list, out of {n} slot",
    countSpoken_other: "{count} on the list, out of {n} slots",
    sourcesUp: "Sources {up}/{all}",
    sourcesDownSpoken_one: "{n} source did not answer",
    sourcesDownSpoken_other: "{n} sources did not answer",
    whyThese: "Why these",
    startReview: "Start review",

    presetTitle: "{label} preset.",
    presetBody:
      "Same rules and companies, other verticals and investor theses. Arrows show each company's move from the {blue} list.",
    backTo: "Back to {blue}",
    dropped: "Dropped under this preset: {names}",

    slotsLeftEmpty_one: "{n} slot left empty on purpose.",
    slotsLeftEmpty_other: "{n} slots left empty on purpose.",
    alwaysOn: "Always on: re-ranked when a source updates.",
    updatedAt: "Updated {stamp}.",
    whyTheseN: "Why these {n}",
    rules: "Rules",

    nothingQualifies: "Nothing qualifies right now",
    neverPadded: "The list is never padded. It updates when a source does.",

    groupFilter: "Show group",
    signalFilter: "Filter by signal",
    all: "All",
    hintMove: "move",
    hintOpen: "open",
    hintClose: "close",
    noneMatch: "No company on the list matches these filters.",
    clearFilters: "Clear filters",

    colCompany: "Company",
    colWhy: "Why it surfaced",
    colSector: "Sector",
    colSignal: "Signal",
    colPotential: "Potential",
    colEvidence: "Evidence",
    colSources: "Sources",
    colDeadline: "Deadline",
    otherReasons: "Other reasons",
    sectorUnknown: "Unknown",
    colNext: "Next step",
    rule_act_now: "High potential and solid evidence.",
    rule_dive_deeper:
      "Promising, but the evidence is thin. Missing information is the next step, not a low score.",
    rule_not_yet: "Too early or a weak fit today. Re-checked when a source updates.",
    noneThisWeek: "None this week.",
    founded: "Founded {date}",
    foundedUnknown: "Founding date unknown",
    moreReasons: "+{n}",
    moreReasonsSpoken: "Show {n} more reasons",
    showLess: "Show less",
    noSourcedReason: "No sourced reason in this list",
    potential: "Potential {value}",
    evidence: "Evidence {value}",
    openCard: "Open the card",
    rankScore: "Rank score {score}",
    rankScoreSpoken: "Rank score, made of {parts}",
    part_fit: "fit",
    part_signal: "signal",
    part_group: "group",
    part_evidence: "evidence",
    part_potential: "potential",

    card: "Venture card",
    cardOf: "Venture card: {name}",

    rail: "Deadlines, sonar and sources",
    deadlineTitle: "{company}: {action}",
    sources: "Sources",
    digestText:
      "The list goes out as a digest every Monday at 07:00. Sending is off in this workspace.",
  },
  fi: {
    explainer_apelago:
      "Uudet meriyritykset, jotka kannattaa kutsua ohjelmaan, kukin perusteluineen ja seuraavine askelineen. Enintään 10, eikä listaa täytetä väkisin.",
    explainer_redstone:
      "Uudet meriyritykset, joiden kanssa kannattaa käydä ensimmäinen keskustelu, kukin perusteluineen ja seuraavine askelineen. Enintään 10, eikä listaa täytetä väkisin.",
    explainer_climate_apelago:
      "Uudet ilmastoteknologian ja kiertotalouden yritykset, jotka kannattaa kutsua ohjelmaan, kukin perusteluineen ja seuraavine askelineen. Enintään 10, eikä listaa täytetä väkisin.",
    explainer_climate_redstone:
      "Uudet ilmastoteknologian ja kiertotalouden yritykset, joiden kanssa kannattaa käydä ensimmäinen keskustelu, kukin perusteluineen ja seuraavine askelineen. Enintään 10, eikä listaa täytetä väkisin.",
    listFailedTitle: "Listaa ei voitu ladata",
    listFailedBody: "Haku ({keys}), Perustajanäkymä ja Tarkkuus toimivat edelleen.",
    retry: "Yritä uudelleen",
    loading: "Ladataan: {list}",

    week: "Viikko {n}",
    since: "{when} alkaen",
    countSpoken_one: "{count} listalla, paikkoja {n}",
    countSpoken_other: "{count} listalla, paikkoja {n}",
    sourcesUp: "Lähteet {up}/{all}",
    sourcesDownSpoken_one: "{n} lähde ei vastannut",
    sourcesDownSpoken_other: "{n} lähdettä ei vastannut",
    whyThese: "Miksi nämä",
    startReview: "Aloita läpikäynti",

    presetTitle: "Esiasetus: {label}.",
    presetBody:
      "Samat säännöt ja yritykset, mutta eri toimialat ja sijoittajien teesit. Nuolet näyttävät, miten kunkin yrityksen sija on muuttunut esiasetuksen {blue} listaan verrattuna.",
    backTo: "Palaa esiasetukseen {blue}",
    dropped: "Putoavat pois tällä esiasetuksella: {names}",

    slotsLeftEmpty_one: "{n} paikka jätetty tarkoituksella tyhjäksi.",
    slotsLeftEmpty_other: "{n} paikkaa jätetty tarkoituksella tyhjiksi.",
    alwaysOn: "Aina käynnissä: järjestys lasketaan uudelleen, kun jokin lähde päivittyy.",
    updatedAt: "Päivitetty {stamp}.",
    whyTheseN: "Miksi nämä {n}",
    rules: "Säännöt",

    nothingQualifies: "Yksikään yritys ei täytä ehtoja juuri nyt",
    neverPadded: "Listaa ei täytetä väkisin. Se päivittyy, kun jokin lähde päivittyy.",

    groupFilter: "Näytä ryhmä",
    signalFilter: "Suodata signaalin mukaan",
    all: "Kaikki",
    hintMove: "liiku",
    hintOpen: "avaa",
    hintClose: "sulje",
    noneMatch: "Yksikään listan yritys ei vastaa näitä suodattimia.",
    clearFilters: "Tyhjennä suodattimet",

    colCompany: "Yritys",
    colWhy: "Miksi listalla",
    colSector: "Toimiala",
    colSignal: "Signaali",
    colPotential: "Potentiaali",
    colEvidence: "Näyttö",
    colSources: "Lähteet",
    colDeadline: "Määräaika",
    otherReasons: "Muut perusteet",
    sectorUnknown: "Ei tiedossa",
    colNext: "Seuraava askel",
    rule_act_now: "Korkea potentiaali ja riittävä näyttö.",
    rule_dive_deeper:
      "Lupaava, mutta näyttöä on vähän. Puuttuva tieto on seuraava askel, ei matala pistemäärä.",
    rule_not_yet:
      "Vielä liian aikaista tai sopii nyt heikosti. Arvio tarkistetaan, kun jokin lähde päivittyy.",
    noneThisWeek: "Ei yhtään tällä viikolla.",
    founded: "Perustettu {date}",
    foundedUnknown: "Perustamispäivä ei tiedossa",
    moreReasons: "+{n}",
    moreReasonsSpoken: "Näytä {n} muuta perustetta",
    showLess: "Näytä vähemmän",
    noSourcedReason: "Tällä listalla ei ole perustetta lähteineen",
    potential: "Potentiaali {value}",
    evidence: "Näyttö {value}",
    openCard: "Avaa kortti",
    rankScore: "Järjestyspisteet {score}",
    rankScoreSpoken: "Järjestyspisteet, osatekijät {parts}",
    part_fit: "sopivuus",
    part_signal: "signaali",
    part_group: "ryhmä",
    part_evidence: "näyttö",
    part_potential: "potentiaali",

    card: "Yrityskortti",
    cardOf: "Yrityskortti: {name}",

    rail: "Määräajat, luotain ja lähteet",
    deadlineTitle: "{company}: {action}",
    sources: "Lähteet",
    digestText:
      "Lista lähetetään koosteena joka maanantai klo 7.00. Lähettäminen on pois päältä tässä työtilassa.",
  },
  sv: {
    explainer_apelago:
      "Nya havsbolag som är värda att bjuda in till ett program, vart och ett med skälet och nästa steg. Högst 10, och listan fylls aldrig ut.",
    explainer_redstone:
      "Nya havsbolag som är värda ett första samtal, vart och ett med skälet och nästa steg. Högst 10, och listan fylls aldrig ut.",
    explainer_climate_apelago:
      "Nya bolag inom klimatteknik och cirkulär ekonomi som är värda att bjuda in till ett program, vart och ett med skälet och nästa steg. Högst 10, och listan fylls aldrig ut.",
    explainer_climate_redstone:
      "Nya bolag inom klimatteknik och cirkulär ekonomi som är värda ett första samtal, vart och ett med skälet och nästa steg. Högst 10, och listan fylls aldrig ut.",
    listFailedTitle: "Listan kunde inte laddas",
    listFailedBody: "Sökningen ({keys}), grundarvyn och sidan Träffsäkerhet fungerar fortfarande.",
    retry: "Försök igen",
    loading: "Laddar {list}",

    week: "Vecka {n}",
    since: "sedan {when}",
    countSpoken_one: "{count} på listan, av {n} plats",
    countSpoken_other: "{count} på listan, av {n} platser",
    sourcesUp: "Källor {up}/{all}",
    sourcesDownSpoken_one: "{n} källa svarade inte",
    sourcesDownSpoken_other: "{n} källor svarade inte",
    whyThese: "Varför dessa",
    startReview: "Börja granska",

    presetTitle: "Förinställning: {label}.",
    presetBody:
      "Samma regler och bolag, men andra branscher och investerarteser. Pilarna visar hur varje bolag har flyttat jämfört med listan för {blue}.",
    backTo: "Tillbaka till {blue}",
    dropped: "Faller bort med den här förinställningen: {names}",

    slotsLeftEmpty_one: "{n} plats medvetet lämnad tom.",
    slotsLeftEmpty_other: "{n} platser medvetet lämnade tomma.",
    alwaysOn: "Alltid igång: rangordnas om när en källa uppdateras.",
    updatedAt: "Uppdaterad {stamp}.",
    whyTheseN: "Varför dessa {n}",
    rules: "Regler",

    nothingQualifies: "Inget bolag uppfyller kraven just nu",
    neverPadded: "Listan fylls aldrig ut. Den uppdateras när en källa gör det.",

    groupFilter: "Visa grupp",
    signalFilter: "Filtrera efter signal",
    all: "Alla",
    hintMove: "flytta",
    hintOpen: "öppna",
    hintClose: "stäng",
    noneMatch: "Inget bolag på listan matchar de här filtren.",
    clearFilters: "Rensa filter",

    colCompany: "Bolag",
    colWhy: "Varför på listan",
    colSector: "Bransch",
    colSignal: "Signal",
    colPotential: "Potential",
    colEvidence: "Belägg",
    colSources: "Källor",
    colDeadline: "Tidsfrist",
    otherReasons: "Andra skäl",
    sectorUnknown: "Okänd",
    colNext: "Nästa steg",
    rule_act_now: "Hög potential och tillräckliga belägg.",
    rule_dive_deeper:
      "Lovande, men beläggen är tunna. Det som saknas är nästa steg, inte ett lägre betyg.",
    rule_not_yet:
      "För tidigt eller svag matchning i dag. Kontrolleras på nytt när en källa uppdateras.",
    noneThisWeek: "Inga den här veckan.",
    founded: "Grundat {date}",
    foundedUnknown: "Grundandedatum okänt",
    moreReasons: "+{n}",
    moreReasonsSpoken: "Visa {n} skäl till",
    showLess: "Visa färre",
    noSourcedReason: "Inget skäl med källa på den här listan",
    potential: "Potential {value}",
    evidence: "Belägg {value}",
    openCard: "Öppna kortet",
    rankScore: "Rankningspoäng {score}",
    rankScoreSpoken: "Rankningspoäng, uppdelat på {parts}",
    part_fit: "matchning",
    part_signal: "signal",
    part_group: "grupp",
    part_evidence: "belägg",
    part_potential: "potential",

    card: "Bolagskort",
    cardOf: "Bolagskort: {name}",

    rail: "Tidsfrister, ekolod och källor",
    deadlineTitle: "{company}: {action}",
    sources: "Källor",
    digestText:
      "Listan skickas som en sammanfattning varje måndag kl. 07.00. Utskick är avstängda i den här arbetsytan.",
  },
});

export type SurfacingKey = keyof typeof surfacingMessages.en;
