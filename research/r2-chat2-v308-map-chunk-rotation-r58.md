# Chat 2 — exact-v308 map chunk rotation semantics R58

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R58 is a separate non-canonical class-only semantic review batch adjacent to R53
`ObjectManager`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_FD135EAA84CA72B0CC53`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/c` -> `CLIENT_CLASS_000079`

## `rs/c` -> `MapChunkRotation`

The class is stateless and exposes exactly four static integer transforms.

Two methods rotate one local coordinate pair inside an 8x8 map chunk. Rotation is
normalized with `rotation & 3` and the methods return the expected quarter-turn forms:

- unchanged coordinate;
- coordinate swap;
- `7 - coordinate`;
- swapped/complemented coordinate.

The other two methods perform the same operation for placed objects whose footprint is
larger than one tile. Their complemented forms subtract `size - 1`, preserving the
object's rotated width/height inside the 8x8 destination chunk.

R53 `ObjectManager` consumes these transforms while loading rotated map/object chunks,
where source-local object coordinates and footprints must be mapped into a destination
chunk.

That role is precise enough for the semantic name `MapChunkRotation`.

## Deliberately withheld adjacent helpers

This batch does not name generic terrain-noise/interpolation or local file-loader helpers
whose class-level semantic identity is less unique.

## Naming boundary

This is a semantic recovery name, not a claim of a verbatim original SpawnPK identifier.

## Acceptance boundary

Chat 2 does not promote R58. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_FD135EAA84CA72B0CC53`.
