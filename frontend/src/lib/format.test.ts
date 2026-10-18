// Checks for the format helpers that rewrite backend text. Run from frontend/ (lang.ts needs a document):
//   node --input-type=module -e "globalThis.document = { documentElement: {} };
//     await (await import('vite')).runnerImport('./src/lib/format.test.ts')"
import { setLang, type Lang } from "../i18n/lang";
import { formatEventDate, levelText } from "./format";

let failures = 0;

function expect(name: string, actual: string | null, expected: string): void {
  if (actual === expected) return;
  failures++;
  console.error(`${name}\n  expected: ${expected}\n  actual:   ${actual}`);
}

function inLang(lang: Lang, check: () => void): void {
  setLang(lang);
  check();
}

inLang("en", () => {
  expect(
    "A'Pelago spells out a level",
    levelText("A business model, such as published pricing (BRL 4)", "apelago"),
    "A business model, such as published pricing (business readiness level 4)",
  );
  expect(
    "A'Pelago spells out every level and a range",
    levelText("A grant (IRL 4), or a lab result (TRL 3-4)", "apelago"),
    "A grant (investment readiness level 4), or a lab result (tech readiness level 3-4)",
  );
  expect(
    "A'Pelago drops the ocean impact number",
    levelText("The company's own impact claim mapped to an area (level 1)", "apelago"),
    "The company's own impact claim mapped to an area",
  );
  expect(
    "Redstone keeps the acronyms",
    levelText("Published pricing (BRL 4); impact (level 1)", "redstone"),
    "Published pricing (BRL 4); impact (level 1)",
  );
  expect("A founding date keeps its year", formatEventDate("2026-09-16"), "16 Sep 2026");
});

inLang("fi", () => {
  expect(
    "Finnish words for a level",
    levelText("julkaistu hinnoittelu (BRL 4)", "apelago"),
    "julkaistu hinnoittelu (liiketoiminnan valmiustaso 4)",
  );
  expect(
    "Finnish ocean impact number dropped",
    levelText("vaikutusalueeseen (taso 1)", "apelago"),
    "vaikutusalueeseen",
  );
  expect("A Finnish founding date keeps its year", formatEventDate("2026-09-16"), "16.9.2026");
});

inLang("sv", () => {
  expect(
    "Swedish words for a level",
    levelText("en acceleratorplats (IRL 4)", "apelago"),
    "en acceleratorplats (investeringsmognad på nivå 4)",
  );
  expect(
    "Swedish ocean impact number dropped",
    levelText("kopplat till ett område (nivå 1)", "apelago"),
    "kopplat till ett område",
  );
  expect("A Swedish founding date keeps its year", formatEventDate("2026-09-16"), "16 sep. 2026");
});

if (failures > 0) throw new Error(`${failures} format check(s) failed`);
console.log("format checks passed");
