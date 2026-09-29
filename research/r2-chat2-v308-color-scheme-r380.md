# Chat 2 — RuneLite ColorScheme source recovery R380

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/d` -> `CLIENT_CLASS_000264` -> `ColorScheme`
- proposal: `SEMPROP_D87B232CABEE33A7A804`
- review: `SEMREVIEW_CD3D46D069A211E41D1F`

## Exact palette

The class is a static Color holder. Its exact-v308 palette starts with:

- RGB 220,138,0
- RGBA 220,138,0,120
- 30,30,30
- 40,40,40
- 77,77,77
- 165,165,165
- 60,60,60
- 35,35,35

and continues with the shared green/red/orange/progress, light-green, gold, blue and dark
background colors used by the RuneLite-derived Swing UI.

## Source match

Historical RuneLite/OpenOSRS `net.runelite.client.ui.ColorScheme` is the shared UI-color
holder and preserves the exact leading constants:

- `BRAND_ORANGE = new Color(220, 138, 0)`
- `BRAND_ORANGE_TRANSPARENT = new Color(220, 138, 0, 120)`

The exact v308 class is consumed by the same recovered UI family, including R22
`RuneLiteSkin` and R378 `SwingUtil`.

## Boundary

This is exact source-name recovery, not a descriptive palette alias.

R380 remains non-canonical Chat 2 semantic research only.
