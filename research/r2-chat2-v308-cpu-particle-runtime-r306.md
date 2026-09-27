# Chat 2 — exact-v308 CPU particle pool / renderer R306

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/r/J` -> `CLIENT_CLASS_000781` -> `CpuParticlePool`
- `rs/r/K` -> `CLIENT_CLASS_000782` -> `CpuParticleRenderer`
- review: `SEMREVIEW_6F00226592F2C68FD202`
- unresolved: **0**
- member proposals: **0**

## Existing authority retained

R50 already recovered:

- `ParticleDefinition` -> `rs/r/c`
- `Particle` -> `rs/r/a`

R98 separately recovered the GPU-optimized particle runtime and pool/batch layer.

R306 closes the distinct CPU allocation/render path rather than re-proposing those owners.

## CpuParticlePool

`rs/r/J` owns a 100,000-instance live/recycle authority and preserves the exact diagnostic:

`[CPU] Reached max capacity of particle pool!`

Its allocator accepts one R50 `ParticleDefinition` plus spawn/state coordinates. It creates a new R50 `Particle` when no recycled id exists, otherwise resets and reinitializes the recycled instance before returning it to the live pool.

R30 `Model` calls this allocator directly during model/world particle emission.

## CpuParticleRenderer

Client constructs one `rs/r/K` per R50 `ParticleDefinition`.

Each renderer owns active/removal lists for that definition. Its frame pass:

- ticks each R50 `Particle`;
- returns expired particles to `CpuParticlePool`;
- removes expired entries after traversal;
- projects live particles to screen/depth space;
- alpha-blends particle color into the software `rs/l/C` pixel buffer using the scene depth buffer.

When GPU mode owns rendering, lifecycle updates continue but the software rasterization body is skipped. This cleanly separates R306 from R98's GPU particle subsystem.

## Boundary

R306 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
