import { defineMessages } from "../i18n/messages";

export const resolutionChipMessages = defineMessages({
  en: {
    state_resolved: "Matched",
    state_probable: "Probable match",
    state_ambiguous: "Ambiguous",
    state_unconfirmed: "Unconfirmed",
    state_unresolved: "Not matched",
  },
  fi: {
    state_resolved: "Yhdistetty",
    state_probable: "Todennäköisesti yhdistetty",
    state_ambiguous: "Epäselvä",
    state_unconfirmed: "Vahvistamaton",
    state_unresolved: "Ei yhdistetty",
  },
  sv: {
    state_resolved: "Matchad",
    state_probable: "Trolig matchning",
    state_ambiguous: "Tvetydig",
    state_unconfirmed: "Obekräftad",
    state_unresolved: "Inte matchad",
  },
});
