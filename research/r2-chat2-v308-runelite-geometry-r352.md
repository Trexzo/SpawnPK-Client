# Chat 2 — RuneLite geometry identities R352

Exact authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Recovered with exact-v308 behavior plus historical RuneLite source identity:

- `rs/runelite/a/j` -> `CLIENT_CLASS_000818` -> `RectangleUnion`
- `rs/runelite/a/p` -> `CLIENT_CLASS_000832` -> `WorldPoint`

Review: `SEMREVIEW_E7AF70D200FACB90E54F`

## RectangleUnion

R221 already source-proved four private helper types owned by this exact outer class:
`ChangingState`, `Chunk`, `Segment`, and `Segments`.

Exact-v308 outer behavior sorts rectangle edges, sweeps/updates segment state and emits
`Shapes<SimplePolygon>`, matching historical RuneLite RectangleUnion.

## WorldPoint

Exact-v308 stores final x/y/plane integers and preserves the historical WorldPoint method
surface: coordinate shifts, LocalPoint conversion, scene-bound tests, region identifiers,
distance operations, and instanced-region transforms.

Both names are source-proven. R352 remains non-canonical semantic research only.
