# Chat 2 — RuneLite RectangleUnion R352

Exact authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Retained result

- `rs/runelite/a/j` -> `CLIENT_CLASS_000818` -> `RectangleUnion`
- proposal: `SEMPROP_2272C5C5C41DFCB72C3D`
- review: `SEMREVIEW_F576CC664CCED0EE27F9`

R221 already source-proved four private helpers owned by this exact outer class:
`ChangingState`, `Chunk`, `Segment`, and `Segments`.

Exact-v308 outer behavior sorts rectangle edges, sweeps/updates segment state and emits
`Shapes<SimplePolygon>`, matching historical RuneLite `RectangleUnion`.

## Correction

The initial R352 draft also proposed `rs/runelite/a/p -> WorldPoint`. That proposal is
removed because R19 already owns the exact class as:

- `rs/runelite/a/p`
- `CLIENT_CLASS_000832`
- `WorldPoint`
- review `SEMREVIEW_402B4C2AA42205916457`

R352 therefore retains only the genuinely fresh outer RectangleUnion class.

R352 remains non-canonical semantic research only.
