# Chat 2 — exact-v308 skeleton / animation-frame semantics R43

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R43 is a separate non-canonical class-only semantic review batch. It follows the scene
recovery work but switches into the adjacent classic animation/model support lane.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_5E11D60B98A4A7CF9AA7`
- field/method proposals: **0**

## `rs/K` -> `Skeleton`

The exact frame loader `rs/k` constructs one `rs/K` definition and binds that same
definition to all decoded animation frames in the group.

The core `rs/K` shape is:

- transform count;
- `int[]` transform-type table;
- `int[][]` label/group table;
- optional extended skeletal metadata.

It does not carry the per-frame X/Y/Z values.

During Model animation, each frame transform index selects one transform type and one
label group from this object. Those groups determine which vertex/face groups receive the
frame's translation/rotation/scale/alpha operation.

That is the exact shared animation skeleton / transform-definition role. The conservative
modern semantic name is `Skeleton`.

## `rs/k` -> `AnimationFrame`

Each `rs/k` instance stores:

- one bound `Skeleton` / `rs/K`;
- transform count;
- transform-index array;
- parallel X, Y and Z transform-value arrays.

The loader decodes sparse transform flags, inserts zero/default transforms where required
by the Skeleton transform table, and records the resulting per-transform X/Y/Z values.

`Model` resolves one of these records by frame/sequence id and applies the values against
the attached Skeleton. The blended-animation path consumes two such frame records against
the shared transform definition.

`AnimationFrame` is chosen instead of the broader `Animation` name to keep it distinct
from R28 `SequenceDefinition`, which owns sequence-level frame ordering/duration data.

## Naming boundary

Both names are semantic recovery names. R43 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R43. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_5E11D60B98A4A7CF9AA7`.
