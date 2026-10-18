// Words on a looked-up company: the register's answer, the live card and the website read.
import { defineMessages } from "../i18n/messages";

export const lookupCardMessages = defineMessages({
  en: {
    resultLabel: "Lookup result",
    resultLabelNamed: "Lookup result: {name}",
    registerDownTitle: "The {register} couldn't answer",
    registerDownBody: "Reason given: {detail}. Try again in a minute.",
    registerDownNoReason:
      "No reason was given. Missing data was not counted as zero; try again in a minute.",
    notFoundTitle: "No company with this ID",
    notFoundBody:
      "The register has no company with this ID. Check the number, or search by the company's name.",
    soleTraderTitle: "This ID belongs to a sole trader",
    soleTraderBody:
      "A sole trader is a private person, so BlueWatch shows nothing about them: no name, no address and no results. Lookups work for companies, such as a Finnish Oy, a Norwegian AS or an Estonian OÜ.",
    assessedTitle: "{name} is already assessed.",
    assessedBody: "Its card has the full gap ledger, the sources and the next steps.",
    openCard: "Open the card",
    assessedChip: "Assessed",
    assessedChipTitle: "Already in BlueWatch's assessed set",
    liveChip: "Live from the register",
    recordedChip: "Recorded register data",
    potential: "Potential",
    evidence: "Evidence",
    potentialCaption: "How big the opportunity looks if the claims hold.",
    evidenceCaption: "How much of it is backed by sources we read.",
    unknownsRule: "Unknowns lower evidence, never potential.",
    registerOnly: "Built from register facts only.",
    siteOff:
      "Reading company websites is off in this workspace, so most evidence is still unknown.",
    siteFinding: "Looking for the company's website…",
    siteReading: "Reading {host}…",
    siteNoClaims: "{host} was read, but nothing on it could be checked against a quote.",
    siteNone:
      "No website found: the register lists none, and no site under the company's name shows that it is theirs.",
    siteUnreachable: "{host} couldn't be read right now, so the card shows register facts only.",
    siteTimeout:
      "Reading the website took too long, so the card shows register facts only. Try again in a minute.",
    siteBudget:
      "Today's budget for reading websites is used up, so the card shows register facts only.",
    siteFailed: "The website couldn't be read this time, so the card shows register facts only.",
    siteLimited:
      "The website wasn't read: there have been too many lookups from this connection. Try again in a few minutes.",
    siteHeading: "From the company's website",
    readBy: "Read by Claude from {host} · quote checked",
    foundInRegister: "Website listed in the register",
    foundByName: "Website found by the company's name and shown to be its own",
    moreClaims_one: "Show {n} more claim",
    moreClaims_other: "Show {n} more claims",
    stepsHeading: "Next steps, in order",
    notRecordedTitle: "Not in the recorded data",
    notRecordedBody:
      "Live register lookups are off in this workspace, and this ID is not in the recorded data, which covers the assessed companies and samples of newly registered ones. The company may still exist.",
    closedTitle: "{name} is no longer trading",
    closedBody:
      "Register status: {status}. BlueWatch does not assess closed companies, so it shows no programmes, investors or next steps.",
    status_ceased: "Ceased",
    status_deleted: "Deleted from the register",
    status_bankrupt: "Bankrupt",
    status_liquidation: "In liquidation",
    status_windingUp: "Being wound up",
    status_restructuring: "In restructuring",
  },
  fi: {
    resultLabel: "Haun tulos",
    resultLabelNamed: "Haun tulos: {name}",
    registerDownTitle: "{register} ei vastannut",
    registerDownBody: "Syy: {detail}. Yritä uudelleen hetken kuluttua.",
    registerDownNoReason:
      "Syytä ei kerrottu. Puuttuvaa tietoa ei tulkittu nollaksi. Yritä uudelleen hetken kuluttua.",
    notFoundTitle: "Tunnuksella ei löytynyt yritystä",
    notFoundBody:
      "Rekisterissä ei ole yritystä tällä tunnuksella. Tarkista tunnus tai hae yrityksen nimellä.",
    soleTraderTitle: "Tunnus kuuluu yksityiselle elinkeinonharjoittajalle",
    soleTraderBody:
      "Yksityinen elinkeinonharjoittaja on yksityishenkilö, joten BlueWatch ei näytä hänestä mitään: ei nimeä, osoitetta eikä tuloksia. Haku toimii yhtiöille, kuten suomalaisille osakeyhtiöille (Oy), norjalaisille AS-yhtiöille ja virolaisille OÜ-yhtiöille.",
    assessedTitle: "{name} on jo arvioitu.",
    assessedBody: "Yrityskortilta löytyvät koko tietoaukkoluettelo, lähteet ja seuraavat askeleet.",
    openCard: "Avaa yrityskortti",
    assessedChip: "Arvioitu",
    assessedChipTitle: "Mukana BlueWatchin arvioimissa yrityksissä",
    liveChip: "Suoraan rekisteristä",
    recordedChip: "Tallennettu rekisteritieto",
    potential: "Potentiaali",
    evidence: "Näyttö",
    potentialCaption: "Kuinka suurelta mahdollisuus näyttää, jos väitteet pitävät paikkansa.",
    evidenceCaption: "Kuinka suuri osa siitä perustuu lähteisiin, jotka olemme lukeneet.",
    unknownsRule: "Puuttuva tieto heikentää näyttöä, ei koskaan potentiaalia.",
    registerOnly: "Perustuu pelkkiin rekisteritietoihin.",
    siteOff:
      "Yritysten verkkosivujen lukeminen on pois päältä tässä työtilassa, joten suurin osa näytöstä puuttuu vielä.",
    siteFinding: "Etsitään yrityksen verkkosivustoa…",
    siteReading: "Luetaan sivustoa {host}…",
    siteNoClaims:
      "Sivusto {host} luettiin, mutta siltä ei löytynyt yhtään väitettä, jonka voisi tarkistaa lainauksesta.",
    siteNone:
      "Verkkosivustoa ei löytynyt: rekisterissä ei ole sivustoa, eikä mikään yrityksen nimellä löytyvä sivusto osoita kuuluvansa sille.",
    siteUnreachable:
      "Sivustoa {host} ei voitu lukea juuri nyt, joten kortilla ovat vain rekisteritiedot.",
    siteTimeout:
      "Verkkosivuston lukeminen kesti liian kauan, joten kortilla ovat vain rekisteritiedot. Yritä uudelleen hetken kuluttua.",
    siteBudget:
      "Päivän kiintiö verkkosivujen lukemiseen on käytetty, joten kortilla ovat vain rekisteritiedot.",
    siteFailed:
      "Verkkosivustoa ei tällä kertaa voitu lukea, joten kortilla ovat vain rekisteritiedot.",
    siteLimited:
      "Verkkosivustoa ei luettu, koska tästä yhteydestä on tehty liian monta hakua. Yritä uudelleen muutaman minuutin kuluttua.",
    siteHeading: "Yrityksen verkkosivuilta",
    readBy: "Claude luki sivustolta {host} · lainaus tarkistettu",
    foundInRegister: "Sivusto on merkitty rekisteriin",
    foundByName: "Sivusto löytyi yrityksen nimellä, ja se on todettu yrityksen omaksi",
    moreClaims_one: "Näytä {n} väite lisää",
    moreClaims_other: "Näytä {n} väitettä lisää",
    stepsHeading: "Seuraavat askeleet järjestyksessä",
    notRecordedTitle: "Ei tallennetussa aineistossa",
    notRecordedBody:
      "Reaaliaikaiset rekisterihaut ovat pois päältä tässä työtilassa, eikä tätä tunnusta ole tallennetussa aineistossa, joka kattaa arvioidut yritykset ja otokset vasta rekisteröidyistä yrityksistä. Yritys voi silti olla olemassa.",
    closedTitle: "{name} ei enää harjoita liiketoimintaa",
    closedBody:
      "Tila rekisterissä: {status}. BlueWatch ei arvioi toimintansa lopettaneita yrityksiä, joten ohjelmia, sijoittajia ja seuraavia askeleita ei näytetä.",
    status_ceased: "Lakannut",
    status_deleted: "Poistettu rekisteristä",
    status_bankrupt: "Konkurssissa",
    status_liquidation: "Selvitystilassa",
    status_windingUp: "Purkautumassa",
    status_restructuring: "Yrityssaneerauksessa",
  },
  sv: {
    resultLabel: "Sökresultat",
    resultLabelNamed: "Sökresultat: {name}",
    registerDownTitle: "{register} svarade inte",
    registerDownBody: "Orsak: {detail}. Försök igen om en stund.",
    registerDownNoReason:
      "Ingen orsak angavs. Uppgifter som saknas räknades inte som noll. Försök igen om en stund.",
    notFoundTitle: "Inget bolag med det här numret",
    notFoundBody:
      "Registret har inget bolag med det här numret. Kontrollera numret eller sök på bolagets namn.",
    soleTraderTitle: "Numret tillhör en enskild näringsidkare",
    soleTraderBody:
      "En enskild näringsidkare är en privatperson, så BlueWatch visar ingenting om personen: inget namn, ingen adress och inga resultat. Sökningen fungerar för bolag, till exempel finländska Oy, norska AS och estniska OÜ.",
    assessedTitle: "{name} har redan bedömts.",
    assessedBody: "Bolagskortet har hela luckregistret, källorna och nästa steg.",
    openCard: "Öppna bolagskortet",
    assessedChip: "Bedömt",
    assessedChipTitle: "Finns redan bland BlueWatchs bedömda bolag",
    liveChip: "Direkt från registret",
    recordedChip: "Sparade registeruppgifter",
    potential: "Potential",
    evidence: "Belägg",
    potentialCaption: "Hur stor möjligheten ser ut att vara om påståendena håller.",
    evidenceCaption: "Hur mycket av det som stöds av källor vi har läst.",
    unknownsRule: "Okända uppgifter sänker beläggen, aldrig potentialen.",
    registerOnly: "Bygger enbart på registeruppgifter.",
    siteOff:
      "Läsning av bolagens webbplatser är avstängd i den här arbetsytan, så de flesta beläggen saknas ännu.",
    siteFinding: "Letar efter bolagets webbplats…",
    siteReading: "Läser {host}…",
    siteNoClaims: "{host} lästes, men inget påstående där kunde kontrolleras mot ett citat.",
    siteNone:
      "Ingen webbplats hittades: registret anger ingen, och ingen webbplats med bolagets namn visar att den är bolagets.",
    siteUnreachable: "{host} gick inte att läsa just nu, så kortet visar bara registeruppgifter.",
    siteTimeout:
      "Det tog för lång tid att läsa webbplatsen, så kortet visar bara registeruppgifter. Försök igen om en stund.",
    siteBudget:
      "Dagens budget för att läsa webbplatser är förbrukad, så kortet visar bara registeruppgifter.",
    siteFailed:
      "Webbplatsen gick inte att läsa den här gången, så kortet visar bara registeruppgifter.",
    siteLimited:
      "Webbplatsen lästes inte eftersom för många sökningar har gjorts från den här anslutningen. Försök igen om några minuter.",
    siteHeading: "Från bolagets webbplats",
    readBy: "Läst av Claude från {host} · citatet kontrollerat",
    foundInRegister: "Webbplatsen finns i registret",
    foundByName: "Webbplatsen hittades via bolagets namn och har visats vara bolagets egen",
    moreClaims_one: "Visa {n} påstående till",
    moreClaims_other: "Visa {n} påståenden till",
    stepsHeading: "Nästa steg i ordning",
    notRecordedTitle: "Finns inte i den sparade datan",
    notRecordedBody:
      "Direktsökningar i registren är avstängda i den här arbetsytan, och numret finns inte i den sparade datan, som täcker de bedömda bolagen och urval av nyregistrerade bolag. Bolaget kan ändå finnas.",
    closedTitle: "{name} bedriver inte längre verksamhet",
    closedBody:
      "Status i registret: {status}. BlueWatch bedömer inte bolag som har upphört, så inga program, investerare eller nästa steg visas.",
    status_ceased: "Upphört",
    status_deleted: "Avregistrerat",
    status_bankrupt: "I konkurs",
    status_liquidation: "I likvidation",
    status_windingUp: "Under avveckling",
    status_restructuring: "I företagssanering",
  },
});
