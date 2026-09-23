# Chat 2 — exact-v308 CollisionMap semantics R39

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R39 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R38 candidate batches.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_BC5E6AB3E6207F6BD98B`
- field/method proposals: **0**

## `rs/f` -> `CollisionMap`

This identity is fixed by exact v308 behavior rather than by class-name analogy.

### Grid

The class owns one `int[104][104]` grid. Its reset routine assigns a special blocked
border value to the outside ring and an interior initialization flag to the remaining
tiles.

### Directional wall clipping

Wall-placement logic updates both the requested tile and the reciprocal neighboring tile.
The masks use the expected directional bit pairs:

- west/east: `128` / `8`
- north/south: `2` / `32`
- diagonal directions: `1`, `4`, `16`, `64`

The projectile/impenetrable path applies the corresponding higher-order reciprocal mask
family, including `1024`, `4096`, `16384` and `65536`.

Matching removal operations clear those same directional relationships.

### Object clipping and reachability

Other methods set or clear rectangular object-blocking masks across tile areas and expose
movement/reachability predicates that examine directional clipping flags while deciding
whether one tile or object boundary can be approached from another.

That combination is precisely the role of the client's tile collision/clipping map.

`CollisionMap` is therefore the conservative semantic name for `rs/f`.

## Acceptance boundary

Chat 2 does not promote R39. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to
`SEMREVIEW_BC5E6AB3E6207F6BD98B`.
