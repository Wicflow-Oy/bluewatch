// Words on the Funding page. Tier labels come from /api/meta; tier meanings and rule words from ui/tierMessages.
import { defineMessages } from "../../i18n/messages";

export const fundingMessages = defineMessages({
  en: {
    explainer:
      "Grants and programmes a company can apply to. Every tier shows the rule that decides it, where that rule was read, and the deadline.",
    company: "Company",
    loading: "Loading funding tiers",
    errorTitle: "Funding couldn't load",
    errorBody: "Founder view still shows tiers for any business ID.",
    retry: "Retry",
    openFounder: "Open Founder view",
    noCompanyTitle: "No listed company to tier yet",
    noCompanyBody:
      "Tiers are worked out for the companies on this week's list, and it is empty right now. Founder view still shows tiers for any business ID.",
    flipTitle: "Decided by registration country",
    flipNote:
      "SBEP call 4 has no Finnish funder, so the country a company is registered in decides its tier for this call.",
    sameCall: "Same call, same deadline",
    callPage: "Call page ({host})",
    flipSideFailedTitle: "Couldn't load this company.",
    flipSideFailedBody: "The rule is still: no Finnish funder in call 4.",
    tiers: "Tiers",
    tiersFor: "Tiers for {company}",
    noFitTitle: "No grant or programme fits {company} yet",
    noFitBody: "Its unknowns are listed on the card.",
    noMatchTitle: "No instrument matches these filters",
    noMatchBody_one:
      "{company} has {n} tiered instrument; widen the kind, deadline or tier to see it.",
    noMatchBody_other:
      "{company} has {n} tiered instruments; widen the kind, deadline or tier to see them.",
    clearFilters: "Clear filters",
    instruments_one: "{count} instrument",
    instruments_other: "{count} instruments",
    kind: "Kind",
    allKinds: "All kinds",
    deadline: "Deadline",
    anyDate: "Any date",
    within_one: "Within {n} day",
    within_other: "Within {n} days",
    tier: "Tier",
    allTiers: "All tiers",
    rulesTitle: "How tiers are decided",
    rulesNote:
      "A tier says whether a company can apply, not whether it should rely on public funding.",
  },
  fi: {
    explainer:
      "Avustukset ja ohjelmat, joihin yritys voi hakea. Jokaisen kelpoisuusluokan kohdalla näkyvät ratkaiseva sääntö, paikka, josta sääntö luettiin, ja määräaika.",
    company: "Yritys",
    loading: "Ladataan kelpoisuusluokkia",
    errorTitle: "Rahoitustietoja ei voitu ladata",
    errorBody: "Perustajanäkymä näyttää kelpoisuusluokat silti mille tahansa yritystunnukselle.",
    retry: "Yritä uudelleen",
    openFounder: "Avaa perustajanäkymä",
    noCompanyTitle: "Listalla ei ole vielä yrityksiä luokiteltavaksi",
    noCompanyBody:
      "Kelpoisuusluokat lasketaan tämän viikon listan yrityksille, ja lista on nyt tyhjä. Perustajanäkymä näyttää luokat silti mille tahansa yritystunnukselle.",
    flipTitle: "Rekisteröintimaa ratkaisee",
    flipNote:
      "SBEP:n neljännessä haussa ei ole suomalaista rahoittajaa, joten yrityksen rekisteröintimaa ratkaisee sen kelpoisuusluokan tässä haussa.",
    sameCall: "Sama haku, sama määräaika",
    callPage: "Hakuilmoitus ({host})",
    flipSideFailedTitle: "Tämän yrityksen tietoja ei voitu ladata.",
    flipSideFailedBody: "Sääntö pätee silti: neljännessä haussa ei ole suomalaista rahoittajaa.",
    tiers: "Kelpoisuusluokat",
    tiersFor: "Kelpoisuusluokat: {company}",
    noFitTitle: "Yritykselle {company} ei vielä löydy sopivaa avustusta tai ohjelmaa",
    noFitBody: "Selvittämättömät asiat näkyvät yrityskortilla.",
    noMatchTitle: "Yksikään rahoitusmuoto ei vastaa suodattimia",
    noMatchBody_one:
      "Yritykselle {company} on luokiteltu {n} rahoitusmuoto. Laajenna tyyppiä, määräaikaa tai luokkaa, niin näet sen.",
    noMatchBody_other:
      "Yritykselle {company} on luokiteltu {n} rahoitusmuotoa. Laajenna tyyppiä, määräaikaa tai luokkaa, niin näet ne.",
    clearFilters: "Tyhjennä suodattimet",
    instruments_one: "{count} rahoitusmuoto",
    instruments_other: "{count} rahoitusmuotoa",
    kind: "Tyyppi",
    allKinds: "Kaikki tyypit",
    deadline: "Määräaika",
    anyDate: "Kaikki määräajat",
    within_one: "{n} päivän sisällä",
    within_other: "{n} päivän sisällä",
    tier: "Luokka",
    allTiers: "Kaikki luokat",
    rulesTitle: "Näin kelpoisuusluokat määräytyvät",
    rulesNote:
      "Kelpoisuusluokka kertoo, voiko yritys hakea, ei sitä, kannattaako sen nojata julkiseen rahoitukseen.",
  },
  sv: {
    explainer:
      "Bidrag och program som ett bolag kan söka. Varje behörighetsnivå visar regeln som avgör den, var regeln lästes och tidsfristen.",
    company: "Bolag",
    loading: "Läser in behörighetsnivåer",
    errorTitle: "Finansieringsuppgifterna kunde inte läsas in",
    errorBody:
      "Grundarvyn visar ändå behörighetsnivåerna för vilket organisationsnummer som helst.",
    retry: "Försök igen",
    openFounder: "Öppna grundarvyn",
    noCompanyTitle: "Inga listade bolag att bedöma ännu",
    noCompanyBody:
      "Behörighetsnivåerna räknas fram för bolagen på veckans lista, och den är tom just nu. Grundarvyn visar ändå nivåerna för vilket organisationsnummer som helst.",
    flipTitle: "Registreringslandet avgör",
    flipNote:
      "I SBEP:s utlysning 4 deltar ingen finländsk finansiär, så landet där bolaget är registrerat avgör dess behörighetsnivå i utlysningen.",
    sameCall: "Samma utlysning, samma tidsfrist",
    callPage: "Utlysningssida ({host})",
    flipSideFailedTitle: "Uppgifterna om det här bolaget kunde inte läsas in.",
    flipSideFailedBody: "Regeln gäller ändå: ingen finländsk finansiär deltar i utlysning 4.",
    tiers: "Behörighetsnivåer",
    tiersFor: "Behörighetsnivåer för {company}",
    noFitTitle: "Inget bidrag eller program passar {company} ännu",
    noFitBody: "Det som är okänt listas på bolagskortet.",
    noMatchTitle: "Ingen finansieringsform matchar filtren",
    noMatchBody_one:
      "{company} har {n} bedömd finansieringsform. Vidga typ, tidsfrist eller nivå för att se den.",
    noMatchBody_other:
      "{company} har {n} bedömda finansieringsformer. Vidga typ, tidsfrist eller nivå för att se dem.",
    clearFilters: "Rensa filter",
    instruments_one: "{count} finansieringsform",
    instruments_other: "{count} finansieringsformer",
    kind: "Typ",
    allKinds: "Alla typer",
    deadline: "Tidsfrist",
    anyDate: "Alla tidsfrister",
    within_one: "Inom {n} dag",
    within_other: "Inom {n} dagar",
    tier: "Nivå",
    allTiers: "Alla nivåer",
    rulesTitle: "Så avgörs behörighetsnivåerna",
    rulesNote:
      "Behörighetsnivån visar om bolaget kan söka, inte om det bör förlita sig på offentlig finansiering.",
  },
});
