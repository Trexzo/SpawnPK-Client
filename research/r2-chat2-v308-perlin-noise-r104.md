# Chat 2 — exact-v308 PerlinNoise R104

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R104 is a separate non-canonical class-only review for the stateless procedural
terrain-height/noise helper split out from R53 `ObjectManager`.

R103 intentionally has no committed semantic review: a temporary `rs/B -> Queue`
proposal was removed after CI correctly exposed that R47 already owns the same class as
`NodeSubList`. The stronger historical Queue/MRUNodes aliases are preserved only as
research evidence.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_7E5DE83AA771BC1BB53C`
- field/method proposals: **0**
- confidence: **0.999**

## Stable ID

- `rs/p` -> `CLIENT_CLASS_000739` -> `PerlinNoise`

## Exact-v308 contract

The top-level terrain-height function combines three octave samples:

- period 4 at `x + 45365`, `z + 91923`;
- period 2 at `x + 10294`, `z + 37821`;
- period 1 at `x`, `z`.

It subtracts/weights the 0..255 noise samples, applies:

`height = (int)(height * 0.3) + 35`

and clamps the result to:

`10 .. 60`.

The same class owns the complete supporting pipeline:

1. scale/period interpolation;
2. smoothed corner/side/center noise;
3. the classic deterministic integer noise hash using:
   - `x + z * 57`;
   - xor with `n << 13`;
   - constants `15731`, `789221`, `1376312589`;
4. cosine interpolation between neighboring samples.

Its static initializer builds 2048-entry fixed-point sine and cosine tables using a
65536 scale and 0.17578125-degree step; cosine interpolation indexes that local table at
`t * 1024 / period`.

## Exact consumer

R53 `ObjectManager` calls the two-coordinate function while decoding terrain.

When a map tile does not provide an explicit height opcode, ObjectManager supplies the
world-offset coordinates to R104, negates the resulting 10..60 value and multiplies it by
8 to produce the base scene height.

This independently fixes the class as procedural terrain noise rather than a generic math
utility.

## Historical-name corroboration

Public deobfuscated RuneScape source preserves a class literally named `PerlinNoise`
whose methods are the same semantic pipeline:

- `getTileHeight`;
- `interpolatedNoise`;
- `smoothNoise`;
- integer `noise`;
- cosine `interpolate`.

317-era `SceneBuilder` / `ObjectManager` source also preserves the same five algorithms
and exact constants before later refactors split them into a dedicated helper.

The public source uses a shared cosine table in some revisions, while exact v308 keeps the
table locally. That implementation detail does not change the semantic identity.

## Acceptance boundary

Chat 2 does not promote R104. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_7E5DE83AA771BC1BB53C`.
