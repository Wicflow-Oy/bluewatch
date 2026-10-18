// Founder view text. The page name comes from the shell; register facts, rules and investor fit labels
// arrive from the API in the interface language.
import { defineMessages } from "../../i18n/messages";

export const founderMessages = defineMessages({
  en: {
    explainer:
      "Type a business ID to see what the company can apply to, which investors fit, and what to do in the next 30 days.",
    lookUpTitle: "Look up",
    privacyTitle: "What happens to what you type",
    privacyStored: "Nothing you type is stored or logged.",
    privacyRegister: "The ID goes only to the official register for that country.",
    privacySoleTraders: "Sole traders are private people: we show nothing about them.",
    refusal_checkDigit: "The check digit doesn't match. Check the ID for a typo.",
    refusal_rateLimited: "The lookup limit has been reached for now. Try again later.",

    previewTitle: "What you'll see",
    previewTiers: "Funding tiers with the rule that decides each one",
    previewFits: "Programmes and investors that fit",
    previewNext: "What to do in the next 30 days",
    loading: "Looking up the business ID",
    tryAgain: "Try again",
    failedTitle: "The lookup couldn't finish",
    failedBody:
      "Something went wrong reading the answer. Nothing you typed was stored, and the rest of BlueWatch still works.",
    closedTitle: "No longer trading",
    soleTraderTitle: "This ID belongs to a sole trader",
    soleTraderBody:
      "A sole trader is a private person, so BlueWatch shows nothing about them: no name, no address and no results. Founder view works for limited companies, such as an Oy, an AS or an OÜ.",
    notFoundTitle: "No company with this ID in the register",
    notFoundBody: "Check the ID for a typo. Nothing you typed was stored.",
    registerDownTitle: "The register couldn't answer",
    registerDown:
      "{register} couldn't answer right now. Nothing was counted as zero. Try again in a minute.",
    registerDownRetry: "{register} couldn't answer right now. Try again in a minute.",
    registerDownReason: "Reason: {detail}",
    notRecordedTitle: "Not in the recorded data",
    notRecordedBody:
      "Live register lookups are off in this workspace, and this business ID isn't in the recorded data. The company may still exist. Nothing you typed was stored.",
    register_FI: "The Finnish company register (PRH)",
    register_NO: "The Norwegian company register (Brreg)",
    register_EE: "The Estonian company register (RIK)",

    openCard: "Open the full card",
    recordedAt: "Recorded {stamp}",
    fact_businessId: "Business ID",
    fact_form: "Company form",
    fact_founded: "Founded",
    fact_municipality: "Municipality",
    fact_industry: "Industry code",
    unknown: "Unknown",
    unknownWhy: "The register's record doesn't say",
    themesLabel: "Themes from the register's industry code",
    themesUnknown: "Unknown until the company says what it does",
    theme_fishProcessing: "fish processing",
    theme_shipbuilding: "shipbuilding",
    theme_shipRepair: "ship repair",
    theme_portServices: "port and water transport services",
    theme_fishing: "fishing and aquaculture",
    theme_waterTransport: "water transport",
    theme_waterSupply: "water supply",
    theme_wastewater: "wastewater",
    theme_software: "software",
    theme_engineering: "engineering and technical consultancy",
    theme_research: "research and development",

    comparedWith: "Compared with {name} ({country})",
    tiersChanged: "Tier changed for {count} calls",
    noTierChanges: "Every funding tier is the same for both companies.",
    changesTo: "changes to",

    nextTitle: "Next 30 days",
    steps_one: "{n} step",
    steps_other: "{n} steps",
    nothingSoon:
      "Nothing closes in the next 30 days. The funding tiers list every call with its deadline.",
    undatedTitle: "Without a deadline",

    investorsTitle: "Investors",
    matches_one: "{n} match",
    matches_other: "{n} matches",
    noInvestors: "No investor fits this company yet. The funding tiers still apply.",
    fitsNow: "Fits now",
    later: "Later",
    showMore: "Show {n} more",

    tiersTitle: "Funding tiers",
    calls_one: "{n} call",
    calls_other: "{n} calls",
    callsPerTier: "Calls per tier",
    noTiers:
      "No grant or programme rule could be checked for this company yet. Its register profile above is all we have.",
    countryDecided: "Decided by registration country",
    researchedBasis:
      "These tiers use the researched facts behind the full card, so the two always agree.",

    programmesTitle: "Programmes",
    programmes_one: "{n} programme",
    programmes_other: "{n} programmes",
    noProgrammes:
      "No programme fits this company yet. The funding tiers show what would change that.",
    noProgrammesNamed:
      "No programme fits {name} yet. The funding tiers show what would change that.",

    shareButton: "Share with A'Pelago",
    shareOff: "Sharing is off in this workspace.",
    shareUnavailable: "Sharing isn't available right now. Nothing was sent.",
    shareTitle: "Share this profile with A'Pelago?",
    shareBody:
      "With sharing on, A'Pelago would receive this company's register profile and these results, and could invite it to a programme. Sharing is off in this workspace, so nothing is stored or sent.",
    cancel: "Cancel",
    share: "Share",
  },
  fi: {
    explainer:
      "Syötä yritystunnus, niin näet, mitä rahoitusta yritys voi hakea, mitkä sijoittajat sopivat ja mitä kannattaa tehdä seuraavan 30 päivän aikana.",
    lookUpTitle: "Haku",
    privacyTitle: "Mitä syöttämillesi tiedoille tapahtuu",
    privacyStored: "Mitään syöttämääsi ei tallenneta eikä kirjata lokiin.",
    privacyRegister: "Tunnus välitetään vain kyseisen maan viralliseen rekisteriin.",
    privacySoleTraders:
      "Yksityiset elinkeinonharjoittajat ovat yksityishenkilöitä, joten heistä ei näytetä mitään.",
    refusal_checkDigit: "Tarkistusmerkki ei täsmää. Tarkista, onko tunnuksessa kirjoitusvirhe.",
    refusal_rateLimited:
      "Hakujen enimmäismäärä on toistaiseksi täyttynyt. Yritä myöhemmin uudelleen.",

    previewTitle: "Tuloksessa näet",
    previewTiers: "Kelpoisuusluokat ja kunkin luokan ratkaiseva sääntö",
    previewFits: "Sopivat ohjelmat ja sijoittajat",
    previewNext: "Mitä kannattaa tehdä seuraavan 30 päivän aikana",
    loading: "Haetaan yritystunnuksella",
    tryAgain: "Yritä uudelleen",
    failedTitle: "Haku ei onnistunut",
    failedBody:
      "Vastauksen lukemisessa tapahtui virhe. Mitään syöttämääsi ei tallennettu, ja BlueWatchin muut osat toimivat normaalisti.",
    closedTitle: "Ei enää toiminnassa",
    soleTraderTitle: "Tunnus kuuluu yksityiselle elinkeinonharjoittajalle",
    soleTraderBody:
      "Yksityinen elinkeinonharjoittaja on yksityishenkilö, joten BlueWatch ei näytä hänestä mitään: ei nimeä, ei osoitetta eikä tuloksia. Perustajanäkymä on tarkoitettu yhtiöille, kuten Oy, AS tai OÜ.",
    notFoundTitle: "Rekisterissä ei ole yritystä tällä tunnuksella",
    notFoundBody: "Tarkista, onko tunnuksessa kirjoitusvirhe. Mitään syöttämääsi ei tallennettu.",
    registerDownTitle: "Rekisteri ei vastannut",
    registerDown:
      "{register} ei vastannut juuri nyt. Mitään ei laskettu nollaksi. Yritä uudelleen hetken kuluttua.",
    registerDownRetry: "{register} ei vastannut juuri nyt. Yritä uudelleen hetken kuluttua.",
    registerDownReason: "Syy: {detail}",
    notRecordedTitle: "Tunnusta ei ole tallennetussa aineistossa",
    notRecordedBody:
      "Reaaliaikaiset rekisterihaut ovat pois päältä tässä työtilassa, eikä tätä yritystunnusta ole tallennetussa aineistossa. Yritys voi silti olla olemassa. Mitään syöttämääsi ei tallennettu.",
    register_FI: "Kaupparekisteri (PRH)",
    register_NO: "Norjan yritysrekisteri (Brreg)",
    register_EE: "Viron yritysrekisteri (RIK)",

    openCard: "Avaa koko yrityskortti",
    recordedAt: "Tallenne {stamp}",
    fact_businessId: "Yritystunnus",
    fact_form: "Yhtiömuoto",
    fact_founded: "Perustettu",
    fact_municipality: "Kotikunta",
    fact_industry: "Toimialakoodi",
    unknown: "Ei tiedossa",
    unknownWhy: "Rekisteritiedoissa tätä ei mainita",
    themesLabel: "Teemat rekisterin toimialakoodin perusteella",
    themesUnknown: "Ei tiedossa, ennen kuin yritys kertoo, mitä se tekee",
    theme_fishProcessing: "kalanjalostus",
    theme_shipbuilding: "laivanrakennus",
    theme_shipRepair: "laivojen korjaus",
    theme_portServices: "satama- ja vesiliikennepalvelut",
    theme_fishing: "kalastus ja vesiviljely",
    theme_waterTransport: "vesiliikenne",
    theme_waterSupply: "vesihuolto",
    theme_wastewater: "jätevesihuolto",
    theme_software: "ohjelmistot",
    theme_engineering: "tekninen suunnittelu ja konsultointi",
    theme_research: "tutkimus ja kehittäminen",

    comparedWith: "Verrattuna yritykseen {name} ({country})",
    tiersChanged: "Kelpoisuusluokka muuttui {count} haussa",
    noTierChanges: "Kelpoisuusluokat ovat samat molemmille yrityksille.",
    changesTo: "muuttuu luokkaan",

    nextTitle: "Seuraavat 30 päivää",
    steps_one: "{n} askel",
    steps_other: "{n} askelta",
    nothingSoon:
      "Mikään haku ei pääty seuraavan 30 päivän aikana. Kelpoisuusluokissa näkyvät kaikki haut määräaikoineen.",
    undatedTitle: "Ilman määräaikaa",

    investorsTitle: "Sijoittajat",
    matches_one: "{n} sopiva",
    matches_other: "{n} sopivaa",
    noInvestors: "Yritykselle ei vielä löydy sopivaa sijoittajaa. Kelpoisuusluokat pätevät silti.",
    fitsNow: "Sopii nyt",
    later: "Myöhemmin",
    showMore: "Näytä {n} lisää",

    tiersTitle: "Kelpoisuusluokat",
    calls_one: "{n} haku",
    calls_other: "{n} hakua",
    callsPerTier: "Haut kelpoisuusluokittain",
    noTiers:
      "Yhdenkään avustuksen tai ohjelman ehtoja ei voitu vielä tarkistaa tälle yritykselle. Käytössä on vain yllä oleva rekisteriprofiili.",
    countryDecided: "Rekisteröintimaa ratkaisee",
    researchedBasis:
      "Luokat perustuvat samoihin selvitettyihin tietoihin kuin koko yrityskortti, joten ne vastaavat aina toisiaan.",

    programmesTitle: "Ohjelmat",
    programmes_one: "{n} ohjelma",
    programmes_other: "{n} ohjelmaa",
    noProgrammes:
      "Yritykselle ei vielä löydy sopivaa ohjelmaa. Kelpoisuusluokista näkee, mikä tilanteen muuttaisi.",
    noProgrammesNamed:
      "Yritykselle {name} ei vielä löydy sopivaa ohjelmaa. Kelpoisuusluokista näkee, mikä tilanteen muuttaisi.",

    shareButton: "Jaa A'Pelagolle",
    shareOff: "Jakaminen on pois päältä tässä työtilassa.",
    shareUnavailable: "Jakaminen ei ole juuri nyt käytettävissä. Mitään ei lähetetty.",
    shareTitle: "Jaetaanko tämä profiili A'Pelagolle?",
    shareBody:
      "Kun jakaminen on päällä, A'Pelago saisi yrityksen rekisteriprofiilin ja nämä tulokset ja voisi kutsua yrityksen ohjelmaan. Jakaminen on pois päältä tässä työtilassa, joten mitään ei tallenneta eikä lähetetä.",
    cancel: "Peruuta",
    share: "Jaa",
  },
  sv: {
    explainer:
      "Ange ett organisationsnummer för att se vad bolaget kan söka, vilka investerare som passar och vad som bör göras de närmaste 30 dagarna.",
    lookUpTitle: "Sökning",
    privacyTitle: "Vad som händer med det du skriver",
    privacyStored: "Inget du skriver sparas eller loggas.",
    privacyRegister: "Numret skickas bara till det officiella registret i landet.",
    privacySoleTraders: "Enskilda näringsidkare är privatpersoner, så vi visar ingenting om dem.",
    refusal_checkDigit: "Kontrollsiffran stämmer inte. Kontrollera att numret är rätt skrivet.",
    refusal_rateLimited: "Gränsen för antalet sökningar är nådd. Försök igen senare.",

    previewTitle: "Det här visas",
    previewTiers: "Behörighetsnivåer med regeln som avgör var och en",
    previewFits: "Program och investerare som passar",
    previewNext: "Vad som bör göras de närmaste 30 dagarna",
    loading: "Söker på organisationsnumret",
    tryAgain: "Försök igen",
    failedTitle: "Sökningen kunde inte slutföras",
    failedBody:
      "Något gick fel när svaret lästes. Inget du skrev sparades, och resten av BlueWatch fungerar som vanligt.",
    closedTitle: "Bedriver inte längre verksamhet",
    soleTraderTitle: "Numret tillhör en enskild näringsidkare",
    soleTraderBody:
      "En enskild näringsidkare är en privatperson, så BlueWatch visar ingenting om personen: inget namn, ingen adress och inga resultat. Grundarvyn fungerar för bolag, till exempel Oy, AS eller OÜ.",
    notFoundTitle: "Registret har inget bolag med det här numret",
    notFoundBody: "Kontrollera att numret är rätt skrivet. Inget du skrev sparades.",
    registerDownTitle: "Registret svarade inte",
    registerDown:
      "{register} svarade inte just nu. Ingenting räknades som noll. Försök igen om en stund.",
    registerDownRetry: "{register} svarade inte just nu. Försök igen om en stund.",
    registerDownReason: "Orsak: {detail}",
    notRecordedTitle: "Numret finns inte i den sparade datan",
    notRecordedBody:
      "Direktsökningar i registren är avstängda i den här arbetsytan, och numret finns inte i den sparade datan. Bolaget kan ändå finnas. Inget du skrev sparades.",
    register_FI: "Handelsregistret (PRH)",
    register_NO: "Det norska företagsregistret (Brreg)",
    register_EE: "Det estniska företagsregistret (RIK)",

    openCard: "Öppna hela bolagskortet",
    recordedAt: "Inspelad {stamp}",
    fact_businessId: "Organisationsnummer",
    fact_form: "Bolagsform",
    fact_founded: "Grundat",
    fact_municipality: "Hemkommun",
    fact_industry: "Branschkod",
    unknown: "Okänt",
    unknownWhy: "Registret anger inte detta",
    themesLabel: "Teman enligt registrets branschkod",
    themesUnknown: "Okänt tills bolaget berättar vad det gör",
    theme_fishProcessing: "fiskberedning",
    theme_shipbuilding: "skeppsbyggnad",
    theme_shipRepair: "fartygsreparationer",
    theme_portServices: "hamn- och sjöfartstjänster",
    theme_fishing: "fiske och vattenbruk",
    theme_waterTransport: "sjöfart",
    theme_waterSupply: "vattenförsörjning",
    theme_wastewater: "avloppshantering",
    theme_software: "programvara",
    theme_engineering: "teknisk konsultverksamhet",
    theme_research: "forskning och utveckling",

    comparedWith: "Jämfört med {name} ({country})",
    tiersChanged: "Behörighetsnivån ändrades för {count} utlysningar",
    noTierChanges: "Behörighetsnivåerna är desamma för båda bolagen.",
    changesTo: "ändras till",

    nextTitle: "De närmaste 30 dagarna",
    steps_one: "{n} steg",
    steps_other: "{n} steg",
    nothingSoon:
      "Ingenting stänger de närmaste 30 dagarna. Behörighetsnivåerna visar varje utlysning med sin tidsfrist.",
    undatedTitle: "Utan tidsfrist",

    investorsTitle: "Investerare",
    matches_one: "{n} träff",
    matches_other: "{n} träffar",
    noInvestors: "Ingen investerare passar bolaget ännu. Behörighetsnivåerna gäller ändå.",
    fitsNow: "Passar nu",
    later: "Senare",
    showMore: "Visa {n} till",

    tiersTitle: "Behörighetsnivåer",
    calls_one: "{n} utlysning",
    calls_other: "{n} utlysningar",
    callsPerTier: "Utlysningar per behörighetsnivå",
    noTiers:
      "Inga villkor för bidrag eller program kunde prövas för bolaget ännu. Registerprofilen ovan är allt vi har.",
    countryDecided: "Avgörs av registreringslandet",
    researchedBasis:
      "Nivåerna bygger på samma kartlagda uppgifter som hela bolagskortet, så de stämmer alltid överens.",

    programmesTitle: "Program",
    programmes_one: "{n} program",
    programmes_other: "{n} program",
    noProgrammes:
      "Inget program passar bolaget ännu. Behörighetsnivåerna visar vad som skulle ändra det.",
    noProgrammesNamed:
      "Inget program passar {name} ännu. Behörighetsnivåerna visar vad som skulle ändra det.",

    shareButton: "Dela med A'Pelago",
    shareOff: "Delning är avstängd i den här arbetsytan.",
    shareUnavailable: "Delning är inte tillgänglig just nu. Ingenting skickades.",
    shareTitle: "Dela den här profilen med A'Pelago?",
    shareBody:
      "Med delning påslagen skulle A'Pelago få bolagets registerprofil och de här resultaten och kunna bjuda in bolaget till ett program. Delning är avstängd i den här arbetsytan, så ingenting sparas eller skickas.",
    cancel: "Avbryt",
    share: "Dela",
  },
});
