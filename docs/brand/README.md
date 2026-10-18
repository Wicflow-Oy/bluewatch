# BlueWatch brand

**The mark is an eye on the waterline.** We watch for what surfaces. The iris sits half in the sea, a hairline wave crosses the lower lid, and below it the eye takes the sea's tint: what is underwater is not yet known. The pupil takes the workspace accent: blue by default, gold in A'Pelago, red in Redstone.

It is one solid form (a pointed almond whose lids leave each corner at about 32 degrees), legible down to 16 px.

| File | Use |
|---|---|
| `mark.svg` | Two-tone mark on dark backgrounds (sidebar, loading screen, share images) |
| `mark-mono.svg` | One colour, inherits `currentColor` (light backgrounds, print, tiny sizes) |
| `favicon.svg` | Browser tab and app icon: the deep-sea gradient tile |

**Geometry (48 grid).**
- Eye: `M2 24 C11 18.2 16.5 12.5 24 12.5 S37 18.2 46 24 C37 30.4 31.5 35.8 24 35.8 S11 30.4 2 24 Z`.
- Iris: a circle at (24, 23.6), r 7.7, cut out.
- Pupil: a circle at (25.8, 21.9), r 3.6.
- Waterline: a 1.7-unit gap that rises gently under the iris (like the water around a floating object): `C36 29.4 30 27.6 24 27.6 S12 29.4 0 29.4`.

**Colours.**
- Above the water: `#F4F7FF`.
- Below the water: `#8DB3FF` on dark (`#9CC0FF` in the tile).
- Pupil: `#4C8DFF`, `#DFAE32` or `#EF1934`.
- Tile gradient: `#2463C7` → `#123A7A` → `#0A1D40` → `#071330`.
- Redstone tile: `#343A46` → `#1A1E26` → `#0C0E13`.

**Wordmark.** "BlueWatch" in Inter SemiBold, tracking −0.03em, set 10 px from a 36 px mark.
