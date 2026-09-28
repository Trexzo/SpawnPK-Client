# Chat 2 — exact-v308 model workspace semantics R38

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R38 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R37 candidate batches.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_5BA47168303B5A8002D7`
- field/method proposals: **0**

## `rs/a/a/a` -> `ModelWorkspace`

This object is passed directly into Model construction as the reusable allocation context.
Model sets its current face/vertex counts and asks it for the arrays used for decoded model
geometry and metadata.

The workspace owns a slot-keyed map of reusable `int[]`, `boolean[]` and `byte[]`
arrays, plus reusable R37 `VertexNormalBuffer` and R34 `FaceNormalBuffer` objects.
Changing the active model dimensions can invalidate/reset those work buffers.

Its nested enum vocabulary is model-specific and survives unobfuscated, fixing the domain.

## `rs/a/a/a$a` -> `ModelElementType`

The enum contains exactly:

- `TRIANGLE`
- `VERTEX`

ModelWorkspace maps those values to the active face/triangle count and vertex count when
sizing slot arrays.

## `rs/a/a/a$b` -> `ModelArraySlot`

The exact surviving slot constants include:

- `FACE_X`, `FACE_Y`, `FACE_Z`
- `COL_X`, `COL_Y`, `COL_Z`
- `INFO`
- `PRIORITIES`
- `ALPHAS`
- `COLOR`
- `VERT_TRANS_GROUPS`
- `VERT_GROUPS`
- `VERT_X`, `VERT_Y`, `VERT_Z`
- `PARTICLES`
- `PARTICLE_PRIORITIES`

Each slot carries one ModelElementType and one ModelArrayType. The enum value is the exact
HashMap key used by ModelWorkspace to allocate/reuse that array.

## `rs/a/a/a$c` -> `ModelArrayType`

The enum contains exactly:

- `INT_ARRAY`
- `FLAG_ARRAY`
- `BYTE_ARRAY`

ModelWorkspace dispatches on it to construct `int[]`, `boolean[]` or `byte[]`
storage for the associated ModelArraySlot.

## Acceptance boundary

Chat 2 does not promote R38. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_5BA47168303B5A8002D7`.
