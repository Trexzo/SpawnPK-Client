# Chat 2 — exact-v308 scene container semantics R40

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R40 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R39 candidate batches.

## Deterministic review result

- candidate classes: **7**
- resolved proposals: **7**
- unresolved: **0**
- review ID: `SEMREVIEW_F2CFA1AE53BAA1DF13C7`
- field/method proposals: **0**

## Scene ownership graph

The exact-v308 scene controller `rs/V` owns a three-dimensional `rs/H[][][]` tile grid,
terrain-height state, temporary scene-object arrays, visibility/occlusion state and the
scene traversal/rendering pipeline.

Its insertion methods construct the following holders and store them into fixed slots on
each tile:

- `rs/U`: two-renderable wall/boundary holder
- `rs/T`: one-renderable wall decoration
- `rs/l`: general scene object, potentially installed across multiple tiles
- `rs/m`: singleton ground/floor decoration
- `rs/n`: three-renderable stacked ground-item pile

The tile itself also owns the paint/model surface structures recovered separately in the
next scene-geometry lane.

## Proposed names

- `rs/V` -> `Scene`
- `rs/H` -> `SceneTile`
- `rs/U` -> `WallObject`
- `rs/T` -> `WallDecoration`
- `rs/l` -> `GameObject`
- `rs/m` -> `GroundDecoration`
- `rs/n` -> `GroundItemPile`

### SceneTile

`SceneTile` is created from plane/x/y coordinates and stored directly in the 3D Scene
grid. It owns both tile-surface representations and every fixed scene-entity slot listed
above, plus the per-tile GameObject array and a linked tile reference.

### GameObject

Unlike the singleton decoration slots, one `GameObject` carries tile-boundary coordinates
and is inserted by reference into every SceneTile intersecting its footprint. A tile can
hold up to five of these objects and tracks edge masks for them.

### WallObject / WallDecoration

The wall holder has two Renderable references and reciprocal orientation masks. The
wall-decoration holder is a distinct singleton with one Renderable and wall-relative
position/orientation metadata.

### GroundDecoration / GroundItemPile

The ground decoration is a single floor-level Renderable at the tile center. The ground
item pile is a separate holder with three Renderable references and pile-height/tag state.

## Acceptance boundary

Chat 2 does not promote R40. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_F2CFA1AE53BAA1DF13C7`.
