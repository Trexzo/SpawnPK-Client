# Chat 2 — exact-v308 scene entity base semantics R51

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R51 is a separate non-canonical class-only semantic review batch extending R40/R41/R42's
scene recovery.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_229173A6D4F3E5E400D1`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/Q` -> `CLIENT_CLASS_000044`

## `rs/Q` -> `SceneEntity`

This class is the common non-rendering scene-holder base for four concrete R40 objects:

- `rs/l` -> `GameObject`
- `rs/m` -> `GroundDecoration`
- `rs/T` -> `WallDecoration`
- `rs/U` -> `WallObject`

All four extend `rs/Q` directly.

The base contributes three integers. Exact Scene construction writes those inherited fields
consistently as:

- the scene/entity tag;
- world-space X coordinate;
- world-space Y coordinate.

Client also exposes a polymorphic lookup returning `rs/Q`. It searches a SceneTile's
wall, wall-decoration, ground-decoration and GameObject slots and compares the same
inherited tag field before returning the matching object.

The distinction is important:

- `rs/Q` is **not** R30 `Renderable`;
- it is **not** the concrete R40 `GameObject`;
- R40 `GroundItemPile` does not extend it.

The role is therefore a shared base record for concrete objects installed into scene
entity slots. `SceneEntity` is the conservative semantic name.

## Naming boundary

This is a semantic recovery name, not a claim of a verbatim original SpawnPK identifier.

## Acceptance boundary

Chat 2 does not promote R51. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_229173A6D4F3E5E400D1`.
