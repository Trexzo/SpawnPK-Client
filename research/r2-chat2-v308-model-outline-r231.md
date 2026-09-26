# Chat 2 — exact-v308 RuneLite model-outline source recovery R231

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R231 recovers the four real source classes in the exact-v308 model-outline package.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_0E29D2E6D57B3D6291EE`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/b/a` -> `CLIENT_CLASS_001028` -> `IntBlockBuffer`
- `rs/ui/b/b` -> `CLIENT_CLASS_001029` -> `ModelOutlineRenderer`
- `rs/ui/b/b$a` -> `CLIENT_CLASS_001030` -> `PixelDistanceDelta`
- `rs/ui/b/b$b` -> `CLIENT_CLASS_001031` -> `PixelDistanceGroupIndex`

## Source provenance

RuneLite upstream `6e74752caa80fe9cb96cd9b37207e171fa525f07` contains
`net.runelite.client.ui.overlay.outline.IntBlockBuffer` and
`ModelOutlineRenderer`, including the exact two private nested distance records.

Exact v308 preserves:

- fixed 1024-int reusable block allocation;
- outline-width 50 and feather 4 constants;
- 6500-entry projected vertex arrays;
- clip/crop bounds and visited bitset;
- outline pixel block queues;
- precomputed distance group/delta tables;
- face culling and triangle rasterization;
- actor/tile/item/graphics-object/RuneLite-object outline entry points.

The nested classes also match field-for-field:
`PixelDistanceDelta(dx,dy)` and
`PixelDistanceGroupIndex(distance,distanceGroupIndex,alphaMultiply)`.

## Acceptance boundary

Chat 2 does not promote R231. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_0E29D2E6D57B3D6291EE`.
