# Chat 2 — exact-v308 RectangleUnion R478

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/runelite/a/j`
- `CLIENT_CLASS_000818`
- `RectangleUnion`
- proposal: `SEMPROP_2272C5C5C41DFCB72C3D`
- review: `SEMREVIEW_F576CC664CCED0EE27F9`

## Why this is an exact source-identity join

R221 already recovered the four nested classes owned by this exact outer class:

- `rs/runelite/a/j$a` -> `ChangingState`
- `rs/runelite/a/j$b` -> `Chunk`
- `rs/runelite/a/j$d` -> `Segment`
- `rs/runelite/a/j$e` -> `Segments`

Those names came from an exact historical RuneLite `RectangleUnion` source match.

The outer `rs/runelite/a/j` contains the corresponding static polygon/rectangle-union
algorithm and returns the already-recovered `Shapes<SimplePolygon>` representation. Its
nested class family, state transitions and output type all line up with the same historical
source type.

## Stable-ID join

R220 fixes:

- `rs/runelite/a/i` -> `CLIENT_CLASS_000817`

R221 fixes:

- `rs/runelite/a/j$a` -> `CLIENT_CLASS_000819`

Therefore the enclosing top-level `rs/runelite/a/j` is
`CLIENT_CLASS_000818`.

R478 remains non-canonical semantic research only.
