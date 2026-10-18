// The guide's text, one file per language with identical ids and structure. It is documentation, so it
// lives as data next to the page rather than as interface messages.
import type { Lang } from "../../../i18n/lang";
import en from "./en.json";
import fi from "./fi.json";
import sv from "./sv.json";

export interface GuideTable {
  head: string[];
  rows: string[][];
}

export interface GuideSection {
  id: string;
  title: string;
  body: string[];
  points?: string[];
  table?: GuideTable;
}

export interface GuideTrack {
  id: string;
  title: string;
  intro: string;
  sections: GuideSection[];
}

export interface GlossaryEntry {
  term: string;
  definition: string;
}

export interface FaqEntry {
  q: string;
  a: string;
}

export interface GuideContent {
  tracks: GuideTrack[];
  glossary: GlossaryEntry[];
  faq: FaqEntry[];
}

/** The day the text was last checked against the product. */
export const CONTENT_UPDATED = "2026-10-17";

/** The FAQ answers questions about BlueWatch itself, so it sits at the end of that track. */
export const FAQ_TRACK = "bluewatch";

const CONTENT: Record<Lang, GuideContent> = { en, fi, sv };

export function guideContent(lang: Lang): GuideContent {
  return CONTENT[lang];
}

/** The track a link asks for; an unknown or missing id opens the first one. */
export function findTrack(content: GuideContent, id: string | undefined): GuideTrack {
  return content.tracks.find((track) => track.id === id) ?? content.tracks[0];
}
