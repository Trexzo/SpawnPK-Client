# Chat 2 — exact-v308 face-normal semantics R34

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R34 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R33 candidate batches.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_CFFBC28D4FD2056FFFE0`
- field/method proposals: **0**

## `rs/a/d` -> `FaceNormalBuffer`

The class was deliberately withheld in R31-R33 because its compact shape alone did not fix
the semantic noun. Following its exact Model producer and consumer paths resolves that.

### Producer: triangle cross-product normals

`Model.q()` iterates the model's triangle faces. For each face it reads the three vertex
indices, subtracts vertex coordinates to obtain two face-edge vectors, computes the cross
product, bounds/rescales the components, and normalizes the resulting XYZ vector to a
length scale of 256.

For the smooth-shading path those components are accumulated into the per-vertex normal
structure. For the flat-shading path, the exact same normalized XYZ components are written
to `rs/a/d` at the current **face index**.

### Shape

`rs/a/d` stores one packed `int[]` sized as `entryCount * 3` and exposes indexed
get/set/add operations for component 0, 1 and 2. Model allocates it using the model face
count and indexes it with the same loop variable used for the triangle index arrays.

### Consumer: flat-shading lighting

The lighting pass later retrieves all three values for the current face from `rs/a/d`,
multiplies them by the three light-vector components, sums the dot product, divides by the
lighting scale and feeds that intensity into the face-color shading path.

This proves the object is packed per-face normal-vector storage rather than a generic
three-component buffer.

`FaceNormalBuffer` is used because the object owns normals for many faces; naming the
whole container simply `FaceNormal` would imply one vector per object and would be
structurally inaccurate.

## Acceptance boundary

Chat 2 does not promote R34. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to
`SEMREVIEW_CFFBC28D4FD2056FFFE0`.
