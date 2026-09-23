# Chat 2 — exact-v308 particle core semantics R50

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R50 is a separate non-canonical class-only semantic review batch recovering the core of the
client particle engine. Exact v308 behavior is the authority; matching public RSPS particle
source is used only as corroborating lineage evidence.

## Deterministic review result

- candidate classes: **5**
- resolved proposals: **5**
- unresolved: **0**
- review ID: `SEMREVIEW_E9FF46C24FD436486335`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/A` -> `CLIENT_CLASS_000001`
- `rs/M` -> `CLIENT_CLASS_000040`
- `rs/R` -> `CLIENT_CLASS_000045`
- `rs/r/a` -> `CLIENT_CLASS_000783`
- `rs/r/c` -> `CLIENT_CLASS_000785`

## `rs/R` -> `Vector`

The class is the particle engine's three-integer vector value:

- static ZERO instance;
- X/Y/Z getters;
- subtraction;
- scalar division;
- in-place addition;
- component-scaled mixing;
- clone/copy;
- three-component string form.

The particle subsystem uses it for velocity, gravity/velocity-step and spawn-position
arithmetic. A public RSPS particle engine contains a `Vector` class with the same core
surface essentially method-for-method.

## `rs/M` -> `SpawnShape`

This is a one-method strategy interface:

`Vector getPoint(Random)`

ParticleDefinition owns one such strategy and asks it to choose a spawn offset when a
particle is created. The matching public engine calls the exact abstraction
`SpawnShape`.

## `rs/A` -> `PointSpawnShape`

This class implements SpawnShape, stores one Vector and returns a clone of that same point
for every Random input.

ParticleDefinition's default spawn shape is the zero-vector point strategy. This exactly
matches the public `PointSpawnShape` implementation.

## `rs/r/c` -> `ParticleDefinition`

The exact v308 field/behavior layout is the characteristic particle definition:

- start/end size;
- start/end color;
- start/end velocity;
- spawn shape;
- start/end alpha;
- lifespan;
- spawn rate;
- sprite;
- velocity step;
- color step;
- size step;
- alpha step;
- gravity/additional vector state.

Its derivation methods compute the per-tick color/size/alpha/velocity changes consumed by
Particle. The public `ParticleDefinition` exposes the same core configuration layout.

## `rs/r/a` -> `Particle`

This object binds one ParticleDefinition and tracks the live particle state.

Its update path:

1. increments age;
2. marks the particle dead at the definition lifespan;
3. advances color, size and alpha by definition steps;
4. advances position by current velocity;
5. advances velocity by the definition velocity step;
6. applies definition gravity/additional vector movement.

The matching public `Particle` performs the same lifecycle. v308 has optimized the live
position/velocity vectors into integer component fields, but the semantic behavior remains
the same.

## Acceptance boundary

Chat 2 does not promote R50. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_E9FF46C24FD436486335`.
