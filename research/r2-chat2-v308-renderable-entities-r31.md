# Chat 2 — exact-v308 renderable entity semantics R31

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R31 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R30 review batches.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_653F6C30F5704F61FE21`
- field/method proposals: **0**

## Remaining obvious Renderable subclasses

- `rs/a/b` -> `GraphicsObject`
- `rs/a/g` -> `GroundItem`
- `rs/a/l` -> `Projectile`
- `rs/a/m` -> `DynamicObject`

### GraphicsObject

The class extends R30 `Renderable`, binds directly to R28
`SpotAnimationDefinition`, tracks current sequence frame/time and finished state, and
renders the current spot-animation model at a fixed world location.

This is the classic stationary spot-animation / still-graphic scene object. The modern
semantic name `GraphicsObject` is used rather than preserving an historical obfuscated
subclass name.

### GroundItem

The class stores item id and quantity. Its model method resolves R28 `ItemDefinition`
by id and requests the quantity-aware item `Model`. Client world/tile item placement
constructs this exact type.

`GroundItem` deliberately distinguishes the world entity from `ItemDefinition`.

### Projectile

The class owns double-precision world position, horizontal/vertical velocity, speed,
vertical acceleration and trajectory state.

Trajectory setup computes distance and per-tick velocities; updates use trigonometric
yaw/pitch and advance a linked SpotAnimationDefinition sequence. This is unambiguously a
ballistic projectile renderable.

### DynamicObject

The class stores object id, type, orientation, tile/corner-height state and optional
SequenceDefinition animation.

Rendering resolves R28 `ObjectDefinition`, including varbit/config-driven morph state,
then builds the active object model. This is the exact animated/morphing world-object role.

## Excluded adjacent helpers

R31 does not name the small `rs/a/c$a` helper or the remaining unclear `rs/a/d`,
`rs/a/e`, `rs/a/f`, `rs/a/i` classes. Their roles are not yet proven to this
batch's standard.

## Acceptance boundary

Chat 2 does not promote R31. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_653F6C30F5704F61FE21`.
