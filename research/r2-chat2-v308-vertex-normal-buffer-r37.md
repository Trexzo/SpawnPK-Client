# Chat 2 — exact-v308 VertexNormalBuffer semantics R37

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R37 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R36 candidate batches.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_DFC7E83B997CD7A18622`
- field/method proposals: **0**

## `rs/S` -> `VertexNormalBuffer`

R34 established the distinct flat-shading face-normal buffer. R37 follows the smooth
shading path and resolves the corresponding per-vertex accumulator.

### Shape

`rs/S` contains one packed integer array with exactly four values per entry. It provides
indexed get/set/add operations for all four components.

Model allocates this structure using the model **vertex count**.

### Producer

During normal generation, Model computes a normalized XYZ cross-product for each triangle.
For the smooth-shaded face path it adds those same three components into `rs/S` at all
three vertex indices of the face, then increments the fourth component for each affected
vertex.

Therefore one vertex accumulates normals from every adjacent smooth-shaded face.

### Lighting consumer

The lighting pass retrieves those accumulated X/Y/Z values for each vertex and computes
the light-vector dot product. The divisor includes the fourth `rs/S` component, making
that value the contribution/count term used to average or normalize the accumulated
vertex normal before producing the vertex shade.

This separates the roles exactly:

- R34 `FaceNormalBuffer`: one XYZ normal per flat-shaded face.
- R37 `VertexNormalBuffer`: accumulated XYZ + contribution count per smooth-shaded
  vertex.

`VertexNormalBuffer` is therefore the conservative structural name for `rs/S`.

## Acceptance boundary

Chat 2 does not promote R37. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to
`SEMREVIEW_DFC7E83B997CD7A18622`.
