# Chat 2 — exact-v308 RectangleUnion private source-name recovery R221

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R221 is a separate non-canonical class-only review for the four previously-unreviewed private implementation classes inside the already-reviewed `rs/runelite/a/j` RectangleUnion family.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_6ABAD489C02634CEAD13`
- field/method proposals: **0**

## Stable IDs

- `rs/runelite/a/j$a` -> `CLIENT_CLASS_000819` -> `ChangingState`
- `rs/runelite/a/j$b` -> `CLIENT_CLASS_000820` -> `Chunk`
- `rs/runelite/a/j$d` -> `CLIENT_CLASS_000822` -> `Segment`
- `rs/runelite/a/j$e` -> `CLIENT_CLASS_000823` -> `Segments`

R27 already reviews:
- `rs/runelite/a/j` -> `RectangleUnion`;
- `rs/runelite/a/j$c` -> `RectangleUnionRectangle`.

## Upstream source provenance

RuneLite upstream `runelite-api/src/main/java/net/runelite/api/geometry/RectangleUnion.java` at `6e74752caa80fe9cb96cd9b37207e171fa525f07` contains the exact private source classes `ChangingState`, `Chunk`, `Segment`, and `Segments`.

The match is structural and algorithmic, not name adjacency:

- `ChangingState` owns output shapes, scan x, delta and first changed segment and implements touch/finish/move/push;
- `Chunk` extends SimplePolygon and owns the two endpoint Segments, with the same reverse invariant repair;
- `Segment` owns next/previous, Chunk, side flag, y and value;
- `Segments` owns the first Segment and implements findLE, insertAfter and allZero.

## AABB conflict deliberately withheld

The same audit proved `rs/runelite/a/a` is the six-getter RuneLite API `AABB` interface. However R32 already contains an older descriptive `AABB` proposal for the concrete six-int implementation `rs/a/i`.

R221 does not create a duplicate semantic name or silently rewrite R32. The interface/implementation naming conflict is retained for an explicit correction pass.

## Acceptance boundary

Chat 2 does not promote R221. Main/Core may accept any subset only through an explicit `semantic_acceptance_spec` bound to `SEMREVIEW_6ABAD489C02634CEAD13`.
