# Chat 2 — exact-v308 GPU particle runtime R98

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R98 is a separate non-canonical class-only review for the GPU-optimized runtime layer
around R50 `ParticleDefinition`.

These names are deliberately descriptive. Unlike R89/R94/R95, no public source identifier
was found that can honestly be claimed as the surviving original class noun.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_8D6E70473D83F1FE17E0`
- field/method proposals: **0**
- confidence: **0.997** each

## Stable IDs

- `rs/k/c/a` -> `CLIENT_CLASS_000327` -> `GpuParticleInstance`
- `rs/k/c/c` -> `CLIENT_CLASS_000329` -> `GpuParticlePool`
- `rs/k/c/d` -> `CLIENT_CLASS_000330` -> `GpuParticleBatch`

## GpuParticleInstance

The class owns one R50 `ParticleDefinition` and a renderer-oriented copy of live particle
state:

- unique long runtime ID;
- current color;
- current size;
- current alpha;
- age / expired flag;
- world X/Y/Z;
- velocity X/Y/Z;
- model/render grouping metadata.

Initialization copies start values from ParticleDefinition and derives initial velocity from
the definition vectors.

Its tick path mirrors the R50 Particle lifecycle:

1. increment age;
2. expire at definition lifespan;
3. advance color;
4. advance size;
5. advance alpha;
6. integrate world position by velocity;
7. advance velocity by the definition velocity step;
8. apply the optional additional movement/gravity vector.

R87 `GpuRenderer` and R96 `ModelPusher` consume these instances directly when producing
particle vertex/color/alpha staging data.

This is not a duplicate proposal for R50 `Particle`: exact v308 retains both classes.
R50 is the general particle-engine object; R98 is the GPU-optimized runtime representation.

## GpuParticlePool

The global manager owns live and recycled particle-instance collections.

Exact capacity behavior is explicit:

- maximum live particle count: **50,000**;
- exact overflow diagnostic:
  `[GPU] Reached max capacity of particle pool!`

On allocation it either constructs a new GpuParticleInstance or reuses one from the recycle
list, resets its definition/position/render state and reinserts it into the live maps/sets.

The update loop ticks every live instance. Expired particles are removed from active state
and recycled.

The same manager owns keyed GpuParticleBatch allocation/reuse:

- maximum live batch count: **50**;
- inactive batches are aged out after **60,000 ms**.

## GpuParticleBatch

Each batch owns:

- one integer grouping/render key;
- an active primitive list of particle runtime IDs;
- a temporary removal list;
- last-use timestamp.

A batch accepts at most **1,000** particle IDs.

Its cleanup pass resolves every ID through GpuParticlePool and removes entries when:

- the particle no longer exists;
- the particle grouping key changed;
- the particle is dead/recycled.

R96 ModelPusher and the model-render path obtain batches through GpuParticlePool and
iterate their member particles as one keyed render/model group.

## Deliberate exclusion: `rs/k/c/b`

The remaining sibling is definitely particle geometry support, but its class noun is not
yet being guessed.

Direct exact-v308 execution of its two pure mesh methods shows:

- full variant: 216 packed ints = **54 vertices**;
- reduced variant: 72 packed ints = **18 vertices**;
- every vertex is encoded as X/Y/Z/color;
- both are centered on the supplied position and scaled by the supplied radius.

GpuRenderer and ModelPusher select between these two mesh variants while emitting
GpuParticleInstance geometry.

That role is strong enough to keep researching, but not yet strong enough to assert the
best class noun in R98.

## Acceptance boundary

Chat 2 does not promote R98. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_8D6E70473D83F1FE17E0`.
