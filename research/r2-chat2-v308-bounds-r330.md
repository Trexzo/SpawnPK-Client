# Chat 2 — exact-v308 Bounds lineage R330

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/g/a` -> `CLIENT_CLASS_000177` -> `Bounds`
- proposal: `SEMPROP_7E023E2EA223D9262EA7`
- review: `SEMREVIEW_4E74912844D1F6296FC4`

## Exact v308 structure

The class stores exactly four integers.

Its four-argument constructor sets:

- low/origin X + Y through one two-int mutator;
- high/size X + Y through the second two-int mutator.

Its two-argument constructor delegates to:

`(0, 0, width, height)`

The class has no unrelated state.

## Exact client use

The base client `rs/C` creates this object from its live container dimensions after
subtracting standalone-frame insets.

The returned high/size pair is then used as the live client width and height during resize
processing.

## Inherited lineage corroboration

RuneLite/OSRS client lineage contains a class literally named `Bounds` with the same:

- lowX / lowY / highX / highY four-int shape;
- `setLow(int,int)`;
- `setHigh(int,int)`;
- `Bounds(int,int)` delegating to `Bounds(0,0,...)`;
- null `toString()`.

That structure is sufficiently specific to recover the inherited class identity rather than
invent a new SpawnPK-only geometry name.

R330 remains non-canonical semantic research only.
