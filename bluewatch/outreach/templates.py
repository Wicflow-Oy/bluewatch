"""Message texts in Finnish, Swedish and English, and the footer every first message must carry.

The footer follows GDPR Art. 14 and 21(4) and Act 917/2014 §202: it names the sender, says why the
company receives the message, gives the short privacy notice, and ends with a separate stop line.
The sender is the workspace's organisation; its business ID, privacy notice and stop address come from
the env, and until they are set the footer says so instead of showing placeholders. `footer_problems`
is the check that blocks approval when any part is missing. This is research, not legal advice.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

from bluewatch.config import Settings

LANGUAGES = ("fi", "sv", "en")
FOOTER_RULE = "----"


# The organisation each workspace sends as, unless OUTREACH_SENDER_ORG names another.
WORKSPACE_ORGS = {"apelago": "A'Pelago", "redstone": "Redstone"}


@dataclass(frozen=True)
class SenderIdentity:
    """Who sends: an organisation, never a person. Details that are not set stay None, never a placeholder."""

    org: str
    business_id: str | None = None
    address: str | None = None
    stop_address: str | None = None
    privacy_url: str | None = None

    @property
    def complete(self) -> bool:
        return bool(self.business_id and self.stop_address and self.privacy_url)

    @classmethod
    def from_env(cls, settings: Settings, workspace: str = "apelago") -> SenderIdentity:
        def env(name: str) -> str | None:
            return os.environ.get(name, "").strip() or None

        # The stop address defaults to our own team inbox, so a STOP reply reaches us in demos.
        team_inbox = settings.outreach_allowlist[0] if settings.outreach_allowlist else None
        stop_address = env("OUTREACH_STOP_ADDRESS") or team_inbox
        org = env("OUTREACH_SENDER_ORG")
        if org is None:  # the business ID and privacy notice belong to a named sender, not to a workspace default
            return cls(org=WORKSPACE_ORGS[workspace], stop_address=stop_address)
        return cls(
            org=org,
            business_id=env("OUTREACH_SENDER_BUSINESS_ID"),
            address=env("OUTREACH_SENDER_ADDRESS"),
            stop_address=stop_address,
            privacy_url=env("OUTREACH_PRIVACY_URL"),
        )


TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "greeting": "Hello,",
        "intro": "We are {org}, and we like to get to know new ocean and maritime companies early.",
        "noticed_registered": "We noticed that {company} was registered on {date}{place}{work}.",
        "noticed": "We came across {company}{work}.",
        "place": " in {place}",
        "work": ", and that you work on {work}",
        "offer_lead": "We also spotted an opportunity that may be useful for {company}:",
        "hedge": "This is our reading of public information; please check the details at the source.",
        "deadline": "Deadline: {date}.",
        "applies_from": "Applies from: {date}.",
        "source": "Source: {url}",
        "meeting": "Would you be open to a 30-minute intro call in the next two weeks? We would like to hear "
        "what you are building and how we could help.",
        "ask_1": "Before we talk, one short question would help us prepare. A one-line answer is enough.",
        "ask_2": "Before we talk, two short questions would help us prepare. A one-line answer is enough.",
        "answers_use": "We use your answers only to update our notes on your company, and we mark them as "
        "confirmed by the company.",
        "first_touch_close": "If a call does not suit you right now, a short reply is enough and we will send "
        "the details.",
        "sign_off": "Best regards,\n{org}",
        "subject_request_1": "{company}: {topic}, and a 30-minute intro call?",
        "subject_request_2": "{company}: {topic}, and a 30-minute intro call?",
        "subject_first": "{company}: {topic}, and a 30-minute intro call?",
        "f_sender": "Sender: {org} (business ID {business_id}{address}).",
        "f_sender_pending": "Sender: {org}. Its business ID, privacy notice and stop address are added when "
        "sending is switched on.",
        "f_why_register": "Why you receive it: {company} is listed in {register}, and we think the opportunity "
        "above fits it.",
        "f_why_site": "Why you receive it: {company} publishes its details on its own website ({domain}), and we "
        "think the opportunity above fits it.",
        "f_notice": "We process only organisation-level details (company name, business ID, public contact "
        "address and the sources above) on the basis of our legitimate interest in finding promising "
        "companies (GDPR Art. 6(1)(f)). We keep them for up to 12 months after our last contact, unless "
        "you reply and we agree to continue. We did not receive these details from you. You have "
        "the right to access, rectify and erase them, and to complain to the Data Protection "
        "Ombudsman (tietosuoja.fi).",
        "f_privacy": "Privacy notice: {privacy_url}",
        "f_stop": "You can object to these messages at any time, free of charge: reply STOP or write to {stop}. "
        "We will stop at once.",
        "f_stop_reply": "You can object to these messages at any time, free of charge: reply STOP. We will stop "
        "at once.",
    },
    "fi": {
        "greeting": "Hei,",
        "intro": "Olemme {org}, ja haluamme tutustua uusiin meri- ja merenkulkualan yrityksiin jo varhain.",
        "noticed_registered": "Huomasimme, että {company} on rekisteröity {date}{place}.",
        "noticed": "Huomasimme yrityksenne {company}.",
        "place": " ja sen kotipaikka on {place}",
        "work": "",
        "offer_lead": "Löysimme myös mahdollisuuden, josta voisi olla teille hyötyä:",
        "hedge": "Tämä on oma tulkintamme julkisista tiedoista; tarkistattehan yksityiskohdat lähteestä.",
        "deadline": "Määräaika: {date}.",
        "applies_from": "Voimassa alkaen: {date}.",
        "source": "Lähde: {url}",
        "meeting": "Sopisiko teille 30 minuutin esittelypuhelu seuraavan kahden viikon aikana? Haluaisimme "
        "kuulla, mitä rakennatte ja miten voisimme auttaa.",
        "ask_1": "Ennen keskustelua yksi lyhyt kysymys auttaisi meitä valmistautumaan. Yhden rivin vastaus riittää.",
        "ask_2": "Ennen keskustelua kaksi lyhyttä kysymystä auttaisi meitä valmistautumaan. Yhden rivin vastaus "
        "riittää.",
        "answers_use": "Käytämme vastauksia vain yritystänne koskevien muistiinpanojemme päivittämiseen ja "
        "merkitsemme ne yrityksen vahvistamiksi.",
        "first_touch_close": "Jos puhelu ei sovi juuri nyt, lyhyt vastaus riittää, niin lähetämme lisätiedot.",
        "sign_off": "Ystävällisin terveisin\n{org}",
        "subject_request_1": "{company}: {topic} ja 30 minuutin esittelypuhelu?",
        "subject_request_2": "{company}: {topic} ja 30 minuutin esittelypuhelu?",
        "subject_first": "{company}: {topic} ja 30 minuutin esittelypuhelu?",
        "f_sender": "Lähettäjä: {org} (Y-tunnus {business_id}{address}).",
        "f_sender_pending": "Lähettäjä: {org}. Lähettäjän Y-tunnus, tietosuojaseloste ja osoite viestien "
        "kieltämistä varten lisätään, kun viestien lähettäminen otetaan käyttöön.",
        "f_why_register": "Miksi saatte viestin: {company} on merkitty {register}, ja arvioimme yllä mainitun "
        "mahdollisuuden sopivan sille.",
        "f_why_site": "Miksi saatte viestin: {company} julkaisee tietonsa omalla verkkosivustollaan ({domain}), "
        "ja arvioimme yllä mainitun mahdollisuuden sopivan sille.",
        "f_notice": "Käsittelemme vain organisaatiotason tietoja (yrityksen nimi, Y-tunnus, julkinen yhteysosoite "
        "ja yllä mainitut lähteet) oikeutetun etumme perusteella, joka on lupaavien yritysten "
        "löytäminen (tietosuoja-asetuksen 6 artiklan 1 kohdan f alakohta). Säilytämme tietoja enintään "
        "12 kuukautta viimeisestä yhteydenotosta, ellei yrityksenne vastaa ja sovimme jatkosta. Emme "
        "saaneet tietoja teiltä. Teillä on oikeus saada pääsy tietoihin, oikaista ja poistaa ne sekä "
        "tehdä valitus tietosuojavaltuutetulle (tietosuoja.fi).",
        "f_privacy": "Tietosuojaseloste: {privacy_url}",
        "f_stop": "Voitte kieltää nämä viestit milloin tahansa maksutta: vastatkaa STOP tai LOPETA tai "
        "kirjoittakaa osoitteeseen {stop}. Lopetamme heti.",
        "f_stop_reply": "Voitte kieltää nämä viestit milloin tahansa maksutta: vastatkaa STOP tai LOPETA. "
        "Lopetamme heti.",
    },
    "sv": {
        "greeting": "Hej,",
        "intro": "Vi är {org}, och vi vill gärna lära känna nya företag inom havs- och sjöfartsbranschen tidigt.",
        "noticed_registered": "Vi såg att {company} registrerades den {date}{place}.",
        "noticed": "Vi har lagt märke till {company}.",
        "place": " med säte i {place}",
        "work": "",
        "offer_lead": "Vi hittade också en möjlighet som kan vara till nytta för er:",
        "hedge": "Detta är vår tolkning av offentliga uppgifter; kontrollera gärna detaljerna i källan.",
        "deadline": "Sista dag: {date}.",
        "applies_from": "Gäller från: {date}.",
        "source": "Källa: {url}",
        "meeting": "Skulle ni vara öppna för ett introduktionssamtal på 30 minuter de närmaste två veckorna? Vi "
        "vill gärna höra vad ni bygger och hur vi kan hjälpa till.",
        "ask_1": "Inför samtalet skulle en kort fråga hjälpa oss att förbereda oss. Ett svar på en rad räcker.",
        "ask_2": "Inför samtalet skulle två korta frågor hjälpa oss att förbereda oss. Ett svar på en rad räcker.",
        "answers_use": "Vi använder svaren endast för att uppdatera våra anteckningar om ert företag, och vi "
        "markerar dem som bekräftade av företaget.",
        "first_touch_close": "Om ett samtal inte passar just nu räcker det med ett kort svar, så skickar vi "
        "detaljerna.",
        "sign_off": "Med vänliga hälsningar\n{org}",
        "subject_request_1": "{company}: {topic} och ett introduktionssamtal på 30 minuter?",
        "subject_request_2": "{company}: {topic} och ett introduktionssamtal på 30 minuter?",
        "subject_first": "{company}: {topic} och ett introduktionssamtal på 30 minuter?",
        "f_sender": "Avsändare: {org} (FO-nummer {business_id}{address}).",
        "f_sender_pending": "Avsändare: {org}. Avsändarens FO-nummer, dataskyddsbeskrivning och adress för att "
        "avböja meddelanden läggs till när utskicken aktiveras.",
        "f_why_register": "Varför ni får det: {company} är registrerat i {register}, och vi tror att möjligheten "
        "ovan passar företaget.",
        "f_why_site": "Varför ni får det: {company} publicerar sina uppgifter på sin egen webbplats ({domain}), "
        "och vi tror att möjligheten ovan passar företaget.",
        "f_notice": "Vi behandlar endast uppgifter på organisationsnivå (företagsnamn, FO-nummer, offentlig "
        "kontaktadress och källorna ovan) med stöd av vårt berättigade intresse att hitta lovande "
        "företag (GDPR art. 6.1 f). Vi sparar dem högst 12 månader efter vår senaste kontakt, om ni inte "
        "svarar och vi kommer överens om att fortsätta. Vi fick inte uppgifterna av er. Ni har rätt "
        "att få tillgång till uppgifterna, att få dem rättade och raderade och att klaga hos "
        "dataombudsmannen (tietosuoja.fi).",
        "f_privacy": "Dataskyddsbeskrivning: {privacy_url}",
        "f_stop": "Ni kan när som helst invända mot dessa meddelanden, utan kostnad: svara STOPP eller skriv "
        "till {stop}. Vi slutar genast.",
        "f_stop_reply": "Ni kan när som helst invända mot dessa meddelanden, utan kostnad: svara STOPP. Vi slutar "
        "genast.",
    },
}

# Registers by country, in the grammatical form each "why" sentence needs.
REGISTERS: dict[str, dict[str, str]] = {
    "FI": {"en": "the Finnish Trade Register (PRH)", "fi": "kaupparekisteriin (PRH)", "sv": "handelsregistret (PRH)"},
    "NO": {
        "en": "the Norwegian Register of Business Enterprises (Brreg)",
        "fi": "Norjan yritysrekisteriin (Brreg)",
        "sv": "Norges företagsregister (Brreg)",
    },
    "EE": {
        "en": "the Estonian e-Business Register (RIK)",
        "fi": "Viron kaupparekisteriin (RIK)",
        "sv": "Estlands handelsregister (RIK)",
    },
}

# Gap questions by evidence field. They ask about the organisation, never for people's names.
QUESTIONS: dict[str, dict[str, str]] = {
    "customers": {
        "en": "Which customers, pilot sites or partners do you work with today? Organisation names or types are "
        "enough.",
        "fi": "Keiden asiakkaiden, pilottikohteiden tai kumppanien kanssa työskentelette tällä hetkellä? "
        "Organisaatioiden nimet tai tyypit riittävät.",
        "sv": "Vilka kunder, pilotplatser eller partner arbetar ni med i dag? Organisationernas namn eller typ räcker.",
    },
    "product": {
        "en": "What does your product or service do today, and is it in use somewhere yet?",
        "fi": "Mitä tuotteenne tai palvelunne tekee tällä hetkellä, ja onko se jo käytössä jossakin?",
        "sv": "Vad gör er produkt eller tjänst i dag, och används den redan någonstans?",
    },
    "team": {
        "en": "How many people work in the company, and what background does the team bring (for example "
        "technical, industry or sales experience)? No names needed.",
        "fi": "Kuinka monta henkeä yrityksessä työskentelee, ja millaista osaamista tiimillä on (esimerkiksi "
        "tekninen, toimiala- tai myyntiosaaminen)? Nimiä ei tarvita.",
        "sv": "Hur många arbetar i företaget, och vilken bakgrund har teamet (till exempel teknik, bransch eller "
        "försäljning)? Inga namn behövs.",
    },
    "business_model": {
        "en": "Who pays for your product or service, and roughly how is it priced (per project, licence or unit)?",
        "fi": "Kuka maksaa tuotteestanne tai palvelustanne, ja miten se karkeasti hinnoitellaan (projekteittain, "
        "lisensseittäin vai kappaleittain)?",
        "sv": "Vem betalar för er produkt eller tjänst, och hur prissätts den ungefär (per projekt, licens eller "
        "enhet)?",
    },
    "funding": {
        "en": "Has the company raised outside funding or grants so far, and are you planning to?",
        "fi": "Onko yritys saanut ulkopuolista rahoitusta tai avustuksia, ja suunnitteletteko sellaista?",
        "sv": "Har företaget fått extern finansiering eller bidrag hittills, och planerar ni det?",
    },
    "impact": {
        "en": "Which ocean or water impact do you aim for, and do you measure it yet?",
        "fi": "Millaista vaikutusta meriin tai vesistöihin tavoittelette, ja mittaatteko sitä jo?",
        "sv": "Vilken påverkan på hav eller vatten siktar ni på, och mäter ni den redan?",
    },
    "tech": {
        "en": "How far along is the technology: lab tests, a pilot in real conditions, or commercial use?",
        "fi": "Missä vaiheessa teknologia on: laboratoriotesteissä, pilotissa todellisissa olosuhteissa vai "
        "kaupallisessa käytössä?",
        "sv": "Hur långt har tekniken kommit: labbtester, pilot i verklig miljö eller kommersiell användning?",
    },
    "market": {
        "en": "Which markets or customer segments are you focusing on first?",
        "fi": "Mihin markkinoihin tai asiakasryhmiin keskitytte ensin?",
        "sv": "Vilka marknader eller kundsegment fokuserar ni på först?",
    },
}

# Evidence field names vary between the reader, the seed and the rules; questions use these.
QUESTION_FIELD = {
    "customers_or_sites": "customers",
    "customer": "customers",
    "pilot": "customers",
    "team_size": "team",
    "pricing": "business_model",
    "funding_events": "funding",
    "impact_thesis": "impact",
    "trl": "tech",
    "deployment": "tech",
}

# Example answers for the demo's simulated reply, by question topic. Each says it is simulated, so it can't
# be taken for something a company said.
SIMULATED_ANSWERS = {
    "customers": "Simulated reply: two pilot customers, a fish farm and a port",
    "product": "Simulated reply: the service is sold today and in use at two sites",
    "team": "Simulated reply: four people, with technical and maritime backgrounds",
    "business_model": "Simulated reply: customers pay per project",
    "funding": "Simulated reply: no outside funding yet; a grant application is planned",
    "impact": "Simulated reply: less nutrient run-off into the sea, not measured yet",
    "tech": "Simulated reply: piloted in real conditions at one site",
    "market": "Simulated reply: fish farms in Finland and Sweden first",
}
SIMULATED_ANSWER_OTHER = "Simulated reply: the company answered this question"


def simulated_answer(field: str) -> str:
    """The example answer to the question about an evidence field."""
    return SIMULATED_ANSWERS.get(QUESTION_FIELD.get(field, field), SIMULATED_ANSWER_OTHER)


# The offer sentence for each bridge type ({party} is the counterparty).
BRIDGE_SENTENCES: dict[str, dict[str, str]] = {
    "won_before_open_again": {
        "en": "{party} has an open tender in the same class you have won before.",
        "fi": "{party} on avannut tarjouskilpailun samassa hankintaluokassa, jossa olette voittaneet aiemmin.",
        "sv": "{party} har en öppen upphandling i samma klass som ni har vunnit tidigare.",
    },
    "already_works_with": {
        "en": "You already work with {party} in a public project. That relationship could also become a pilot "
        "or a reference customer.",
        "fi": "Teette jo yhteistyötä julkisessa hankkeessa: {party}. Yhteistyöstä voisi kehittyä myös pilotti tai "
        "referenssiasiakkuus.",
        "sv": "Ni samarbetar redan med {party} i ett offentligt projekt. Samarbetet kunde också bli en pilot "
        "eller en referenskund.",
    },
    "rule_decides": {
        "en": "{party}: under its published rules, your company may be eligible.",
        "fi": "{party}: julkaistujen sääntöjen mukaan yrityksenne voi olla hakukelpoinen.",
        "sv": "{party}: enligt de publicerade reglerna kan ert företag vara behörigt att söka.",
    },
    "proof_step": {
        "en": "{party} offers a validation step that fits your technology.",
        "fi": "{party} tarjoaa validointimahdollisuuden, joka sopii teknologiaanne.",
        "sv": "{party} erbjuder ett valideringssteg som passar er teknik.",
    },
    "law_creates_buyer": {
        "en": "A regulation creates buyers for what you offer: {party}.",
        "fi": "Sääntely luo ostajia tarjoamallenne ratkaisulle: {party}.",
        "sv": "En reglering skapar köpare för det ni erbjuder: {party}.",
    },
    "programme_fit": {
        "en": "{party} could be a good fit for you now, as a participant or as a mentor or expert.",
        "fi": "{party} voisi sopia teille nyt, joko osallistujana tai mentorina tai asiantuntijana.",
        "sv": "{party} kan passa er nu, antingen som deltagare eller som mentor eller expert.",
    },
    "lab_window": {
        "en": "{party} supports research teams that are moving towards founding a company.",
        "fi": "{party} tukee tutkimusryhmiä, jotka ovat perustamassa yritystä.",
        "sv": "{party} stöder forskargrupper som är på väg att grunda ett företag.",
    },
}

# The offer sentence for an Opportunity, by kind ({party} is its title). Grants depend on the tier.
OPPORTUNITY_SENTENCES: dict[str, dict[str, str]] = {
    "programme": BRIDGE_SENTENCES["programme_fit"],
    "grant_certain": {
        "en": "{party}: your company appears to meet the published criteria.",
        "fi": "{party}: yrityksenne näyttää täyttävän julkaistut ehdot.",
        "sv": "{party}: ert företag verkar uppfylla de publicerade villkoren.",
    },
    "grant_possible": BRIDGE_SENTENCES["rule_decides"],
    "grant_unknown": {
        "en": "{party}: the criteria are not published yet, so it is worth asking the funder.",
        "fi": "{party}: ehtoja ei ole vielä julkaistu, joten rahoittajalta kannattaa kysyä.",
        "sv": "{party}: villkoren är inte publicerade ännu, så det är värt att fråga finansiären.",
    },
    "investor": {
        "en": "{party} invests in companies at your stage and in your field; a short conversation could be useful.",
        "fi": "{party} sijoittaa teidän vaiheessanne ja alallanne toimiviin yrityksiin; lyhyt keskustelu voisi "
        "olla hyödyllinen.",
        "sv": "{party} investerar i företag i ert skede och inom ert område; ett kort samtal kunde vara till nytta.",
    },
    "buyer": {
        "en": "{party} buys the kind of solution you offer.",
        "fi": "{party} hankkii tarjoamanne kaltaisia ratkaisuja.",
        "sv": "{party} köper den typ av lösning som ni erbjuder.",
    },
    "partner": {
        "en": "{party} could be a pilot or partner for you.",
        "fi": "{party} voisi olla teille pilotti- tai yhteistyökumppani.",
        "sv": "{party} kan vara en pilot- eller samarbetspartner för er.",
    },
}
OPPORTUNITY_SENTENCES["pilot"] = OPPORTUNITY_SENTENCES["partner"]

_MONTHS_EN = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def format_date(day: date, language: str) -> str:
    if language == "en":
        return f"{day.day} {_MONTHS_EN[day.month - 1]} {day.year}"
    return f"{day.day}.{day.month}.{day.year}"


def footer(language: str, identity: SenderIdentity, *, company: str, country: str | None, domain: str | None) -> str:
    t = TEXTS[language]
    register = REGISTERS.get(country or "", {}).get(language)
    if register:
        why = t["f_why_register"].format(company=company, register=register)
    else:
        why = t["f_why_site"].format(company=company, domain=domain or "-")
    if identity.complete:
        address = f", {identity.address}" if identity.address else ""
        sender = t["f_sender"].format(org=identity.org, business_id=identity.business_id, address=address)
    else:
        sender = t["f_sender_pending"].format(org=identity.org)
    privacy = [t["f_privacy"].format(privacy_url=identity.privacy_url)] if identity.privacy_url else []
    stop = t["f_stop"].format(stop=identity.stop_address) if identity.stop_address else t["f_stop_reply"]
    return FOOTER_RULE + "\n" + "\n".join([sender, why, t["f_notice"], *privacy, "", stop])


# The fixed words each footer part must contain, so a missing part is found by a plain check.
_FOOTER_MARKERS = {
    "en": {
        "sender": "Sender: ",
        "reason for contact": "Why you receive it",
        "legal basis": "Art. 6(1)(f)",
        "retention period": "12 months",
    },
    "fi": {
        "sender": "Lähettäjä: ",
        "reason for contact": "Miksi saatte viestin",
        "legal basis": "6 artiklan 1 kohdan f",
        "retention period": "12 kuukautta",
    },
    "sv": {
        "sender": "Avsändare: ",
        "reason for contact": "Varför ni får det",
        "legal basis": "art. 6.1 f",
        "retention period": "12 månader",
    },
}
_STOP_WORDS = {"en": "STOP", "fi": "LOPETA", "sv": "STOPP"}


def footer_problems(body: str, language: str, identity: SenderIdentity, company: str) -> list[str]:
    """The footer parts missing from a message body, in plain words. Empty means complete."""
    if language not in LANGUAGES:
        return [f"there is no footer template for language '{language}'"]
    if f"\n{FOOTER_RULE}\n" not in body:
        return ["the footer is missing"]
    foot = body.rsplit(f"\n{FOOTER_RULE}\n", 1)[1]
    missing = [part for part, marker in _FOOTER_MARKERS[language].items() if marker not in foot]
    if identity.complete and identity.business_id not in foot:
        missing.append("sender identity")
    if company not in foot:
        missing.append("the company the message is about")
    if "tietosuoja.fi" not in foot or (identity.privacy_url and identity.privacy_url not in foot):
        missing.append("privacy notice, rights and complaint")
    # Messages go out as plain text, so the stop line stands apart as the footer's last paragraph,
    # not through markup the recipient would see as stray asterisks.
    paragraphs = [p.strip() for p in foot.split("\n\n")]
    stop_line = paragraphs[-1] if len(paragraphs) > 1 else ""
    if _STOP_WORDS[language] not in stop_line or (identity.stop_address and identity.stop_address not in stop_line):
        missing.append("separate stop line with a stop address")
    return [f"footer: {part} is missing" for part in missing]
