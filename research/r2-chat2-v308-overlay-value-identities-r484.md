# Chat 2 — Overlay value identities R484

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/f/c` -> `CLIENT_CLASS_000484` -> `OverlayBounds`
- `rs/l/f/f` -> `CLIENT_CLASS_000487` -> `OverlayMenuEntry`
- review: `SEMREVIEW_6FB1B06E2FAFB648F712`

## OverlayBounds

Exact-v308 preserves the source-style toString field names:

- topLeft
- topCenter
- topRight
- bottomLeft
- bottomRight
- aboveChatboxRight
- canvasTopRight

The class owns exactly seven Rectangle values, supports copy/translation, maps
OverlayPosition <-> Rectangle and exposes all bounds as a collection.

Historical RuneLite OverlayBounds has the same structure.

## OverlayMenuEntry

Exact-v308 preserves:

`OverlayMenuEntry(menuAction=..., option=..., target=...)`

The class stores menuAction + option + target and one callback
`Consumer<CustomMenuEntry>`. The callback is excluded from value equality, matching
historical RuneLite OverlayMenuEntry behavior.

## Boundary

Names are source-correlated exact-v308 identities. R484 remains non-canonical research only.
