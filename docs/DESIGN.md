# BlueWatch design language: "Tidepool"

BlueWatch is a tool people work in all day. It should feel calm, light and finished: soft white cards on a warm
canvas, pill controls, fluid but quick motion, and evidence as the texture. It is never a marketing page.

## Principles
1. **A tool, not a page.** A frosted top bar with nav pills, a command palette (⌘K), cards and sheets. No hero
   images, no tour.
2. **Colour means something.** Ink for the primary action, cobalt for the product accent and "Act now", sea green
   for facts and evidence, amber for deadlines within 14 days, red for unavailable or excluded, violet for bridges.
   The workspace (A'Pelago or Redstone) only changes its dot colour.
3. **Evidence is the texture.** Numbered source pills, hatched unknowns, mono dates and IDs. Unknowns lower
   evidence, never potential.
4. **Fluid, not slow.** A row grows into the venture card (View Transitions, with a fade fallback), segmented
   controls slide, numbers count up once, lists stagger in. Presses scale slightly. `prefers-reduced-motion`
   turns all of it off, and everything still works.
5. **Every state is designed:** skeletons, a hatched empty state with the next action, errors that say what still
   works, and a visible chip for cached or unavailable sources.

## Tokens and themes
All colours, radii, shadows, spacing, layers and durations are CSS variables in
`frontend/src/styles/tokens.css`; components use tokens only. Two themes with equal care: **Light** (default,
canvas `#F4F4F1`, cards white) and **Graphite** (canvas `#0F1012`, cards `#18191C`, buttons invert).
`public/theme-init.js` sets the theme before paint; `lib/theme.ts` and `shell/ThemeToggle.tsx` switch it.

## Type
- **Instrument Sans** for the UI and titles (page titles 30 px, tight).
- **Geist Mono** for IDs, dates, counts and scores, always tabular.
- Both are self-hosted from pinned `@fontsource-variable` packages (`styles/fonts.css`), so the CSP serves fonts
  from our own origin only.
- Icons: Lucide, 14–16 px, 1.5–1.75 stroke. No emoji.

## Shell
- **Top bar:** app tile and wordmark, the scope pill (workspace dot, preset), nav pills with counts (rarer pages
  under "More"), search, language (EN · FI · SV), theme, guide, alerts and the status avatar. Below 1280 px the
  nav moves to a second row; on phones it becomes a floating tab bar with a "More" sheet.
- **Sheets:** the venture card opens as a large card sheet under the top bar, which stays usable; on phones every
  sheet is a bottom sheet with a grab handle.
- **Shockwave:** a very faint cobalt ring from each click, drawn on the canvas behind the cards.

## Signature pieces
- **Now Surfacing:** capsule rows with rank tiles, P/E mini meters and deadline pills; a rail with the night
  "Due next" card, the **Sonar** (companies as blips by sector, closer to the centre = higher potential, larger =
  more evidence) and the source status.
- **Venture card:** rank tile, segmented tabs, three columns of inset panels: potential and evidence meters,
  readiness tracks, what we know, and next steps as a timeline.

## Copy
- Plain words in English, Finnish and Swedish; Finnish words are long, so nothing clips.
- No acronyms in A'Pelago headings ("Tech readiness", not "TRL"). Never "AI-powered": say what it does.
- No placeholder text anywhere a visitor can reach.
