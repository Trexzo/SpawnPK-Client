# Chat 2 — exact-v308 GPU particle mesh builder R99

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R99 is a separate non-canonical class-only review for the remaining exact-v308
`rs/k/c/*` GPU particle helper.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_44B92BC956ED596303D4`
- field/method proposals: **0**
- confidence: **0.997**

## Stable ID

- `rs/k/c/b` -> `CLIENT_CLASS_000328` -> `GpuParticleMeshBuilder`

## Exact geometry contract

The class is stateless except for reusable static integer output arrays and a static write
cursor.

Both public builders accept:

- center X;
- center Y;
- center Z;
- radius / particle size;
- packed color/alpha.

Each emitted vertex is four consecutive integers:

`X, Y, Z, packedColor`

### Full-detail mesh

The first builder fills:

- **216 ints**
- **54 vertices**
- **18 triangles**

The coordinates are centered on the supplied X/Y/Z and offset symmetrically by the supplied
radius across the three axes.

### Reduced-detail mesh

The second builder fills:

- **72 ints**
- **18 vertices**
- **6 triangles**

It uses the same center/radius/color contract with a reduced geometry surface.

## Exact runtime selection

R87 `GpuRenderer` and R96 `ModelPusher` contain the same selection behavior.

For a GPU particle:

- detail selector `false` -> full mesh -> 18 triangles / 54 vertices;
- detail selector `true` -> reduced mesh -> 6 triangles / 18 vertices.

Immediately before the call, both consumers derive:

- particle world position from R98 `GpuParticleInstance`;
- radius from the particle's current size;
- packed color and alpha from the particle's current state.

The returned integer array is appended directly to R89 `GpuIntBuffer`.

This fixes the class responsibility as GPU particle mesh construction independently of any
English naming guess.

## Naming boundary

No matching historical/public source class noun survived the searches used for R89-R99.

`GpuParticleMeshBuilder` is therefore deliberately **descriptive**, not claimed as an
original developer identifier. Confidence is 0.997 rather than 0.999 for that reason.

The name also distinguishes this helper from:

- R98 `GpuParticleInstance`;
- R98 `GpuParticlePool`;
- R98 `GpuParticleBatch`;
- R96 `ModelPusher`, which consumes the generated geometry but does not own its primitive
  shape generation.

## Acceptance boundary

Chat 2 does not promote R99. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_44B92BC956ED596303D4`.
