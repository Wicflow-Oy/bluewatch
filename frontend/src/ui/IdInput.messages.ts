import { defineMessages } from "../i18n/messages";

export const idInputMessages = defineMessages({
  en: {
    country: "Country of registration",
    businessId: "Business ID",
    lookUp: "Look up",
    hint_FI: "A Finnish business ID looks like 1234567-8.",
    hint_NO: "A Norwegian organisation number has 9 digits.",
    hint_EE: "An Estonian registry code has 8 digits.",
  },
  fi: {
    country: "Rekisteröintimaa",
    businessId: "Yritystunnus",
    lookUp: "Hae",
    hint_FI: "Suomalainen Y-tunnus on muotoa 1234567-8.",
    hint_NO: "Norjalaisessa organisaationumerossa on 9 numeroa.",
    hint_EE: "Virolaisessa rekisterikoodissa on 8 numeroa.",
  },
  sv: {
    country: "Registreringsland",
    businessId: "Organisationsnummer",
    lookUp: "Sök",
    hint_FI: "Ett finskt FO-nummer har formen 1234567-8.",
    hint_NO: "Ett norskt organisationsnummer har 9 siffror.",
    hint_EE: "En estnisk registerkod har 8 siffror.",
  },
});
