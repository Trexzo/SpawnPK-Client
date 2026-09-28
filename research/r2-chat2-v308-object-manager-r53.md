# Chat 2 — exact-v308 ObjectManager semantics R53

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R53 is a separate non-canonical class-only semantic review batch connecting R39
`CollisionMap` with the R40-R42 Scene recovery.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_E80B92D2470E8CC80E1D`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/x` -> `CLIENT_CLASS_001114`

## `rs/x` -> `ObjectManager`

The constructor receives the scene's tile-flag `byte[][][]` and terrain-height
`int[][][]` arrays. The object also owns the working arrays used for underlay/overlay,
tile shape/rotation, lighting/shading and scene-build flags.

Its region-loading methods decode byte arrays into those structures, including rotated
chunk loading and location/object streams.

The object-placement path:

1. decodes object ids, local coordinates, type and orientation;
2. resolves the corresponding R28 `ObjectDefinition`;
3. constructs the correct Renderable / DynamicObject;
4. installs walls, wall decorations, ground decorations or general GameObjects into the
   R40 `Scene`;
5. applies the matching blocking state to R39 `CollisionMap`.

The final terrain build pass computes surface colors and lighting, emits tile paint/model
geometry into Scene, updates bridge/plane state and coalesces scene-occlusion flags into
R42 `Occluder` records.

That exact responsibility set is the classic client terrain/object region builder
historically named `ObjectManager`. Exact v308 behavior is the primary evidence; the
historical name is a corroborating lineage match.

## Naming boundary

R53 uses `ObjectManager` as a semantic/historical recovery name and does not claim an
independent verbatim source recovery beyond the evidence above.

## Acceptance boundary

Chat 2 does not promote R53. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_E80B92D2470E8CC80E1D`.
