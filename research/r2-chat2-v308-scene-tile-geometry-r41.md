# Chat 2 — exact-v308 scene tile geometry semantics R41

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R41 continues directly from R40's Scene / SceneTile container recovery. It is a separate
non-canonical class-only semantic review batch and does not alter Main/Core semantic authority.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_448010991767A7F32856`
- field/method proposals: **0**

## R40 adjacency

R40 recovered:

- `rs/V` -> `Scene`
- `rs/H` -> `SceneTile`

The exact `SceneTile` layout has two mutually distinct tile-surface slots:

- `rs/J h`
- `rs/I i`

R41 resolves those two surface representations.

## `rs/I` -> `SceneTileModel`

`Scene` constructs `rs/I` only for tile shapes outside the two simple paint cases and
stores the result into the modeled-tile slot on `SceneTile`.

The constructor is a full per-tile mesh builder. It uses:

- fixed shape tables;
- fixed rotation tables;
- the classic 128-unit tile grid;
- corner-height interpolation;
- underlay/overlay corner colors;
- per-vertex X/Y/Z arrays;
- triangle-index arrays;
- per-face color arrays;
- optional texture ids.

That is the shaped/triangulated scene-tile representation, so the conservative modern semantic
name is `SceneTileModel`.

## `rs/J` -> `SceneTilePaint`

`Scene` constructs `rs/J` for the two simple tile cases and stores it into the other
dedicated surface slot on `SceneTile`.

The class is deliberately compact compared with `SceneTileModel`: it stores the four corner
surface colors plus texture/overlay metadata and a flatness flag, with only three auxiliary
mutable color values used by the scene render pipeline.

The exact Scene branch separating `rs/J` from the shaped `rs/I` mesh fixes the role as the
simple painted tile surface. The conservative modern semantic name is `SceneTilePaint`.

## Naming boundary

These are semantic recovery names. R41 does not claim that either identifier is a verbatim
original SpawnPK source identifier.

## Acceptance boundary

Chat 2 does not promote R41. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_448010991767A7F32856`.
