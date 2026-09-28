# Chat 2 — exact-v308 scene occluder semantics R42

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R42 is a separate non-canonical class-only semantic review batch following the R40 Scene
container and R41 tile-surface recovery.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_1FB649208BB505C461EE`
- field/method proposals: **0**

## `rs/G` -> `Occluder`

The identity is fixed by the exact `Scene` ownership and activation path.

### Registration

`Scene` has a static eight-integer registration method which:

1. constructs one `rs/G`;
2. stores tile-space min/max bounds;
3. stores corresponding world-space X/Y/Z bounds;
4. stores an occlusion type;
5. appends the record to a per-plane `rs/G[][]` collection.

### Camera/visibility activation

Before scene traversal, `Scene` scans the current plane's registered `rs/G` records.
Depending on the record type, it checks the record's tile range against the current
camera visibility map and rejects records that are not on the relevant side of the camera
or do not intersect visible cells.

Accepted records are copied into a separate active `rs/G[]` list.

### Projection state

For each active record, `Scene` derives camera-relative slope/range values from the
record's stored world bounds. Those derived values are subsequently consumed by the
scene's point/tile/object visibility tests.

That combination is exactly a scene occlusion volume/occluder record. The conservative
modern semantic name is therefore `Occluder`.

## Naming boundary

This is a semantic recovery name, not a claim that `Occluder` is a verbatim original
SpawnPK identifier.

## Acceptance boundary

Chat 2 does not promote R42. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_1FB649208BB505C461EE`.
