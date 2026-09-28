# Chat 2 — exact-v308 Skybox R91

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R91 is a separate non-canonical class-only review batch for the exact skybox mapping/parser
class used by the bundled `skybox.txt` resource.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_69AF0AAE5D5B1F373C29`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/k/o` -> `CLIENT_CLASS_000345`

## `rs/k/o` -> `Skybox`

Exact v308 exposes both:

- `Skybox(InputStream, String)`-shape construction;
- `Skybox(Reader, String)`-shape construction.

The parser grammar is exceptionally identifying. It accepts:

- `bounds` declarations;
- map-region selectors `m`;
- region selectors `r` / `R`;
- chunk selectors `c` / `C`;
- `#RGB` / `#RRGGBB` colors;
- plane masks;
- per-entry blend radius.

The exact regular-expression groups include:

- `mrx` / `mry`;
- `rx` / `ry`;
- `cx` / `cy`;
- `color`;
- `plane`;
- `blend`.

Colors are converted into a YCoCg representation before storage. The class maintains
chunk-level values plus compact plane-specific overrides.

Its point-sampling path:

- optionally maps instance chunks through a three-integer callback;
- reads the selected chunk/plane value;
- performs Gaussian-style spatial blending using an error-function approximation;
- converts the blended YCoCg value back to RGB;
- applies brightness through HSB.

The same object can render the skybox mapping into a `BufferedImage` for inspection.

## Resource identity

Exact v308 `rs/k/p` constructs `rs/k/o` directly from:

`skybox.txt`

This independently fixes the parser's data domain.

R91 deliberately does **not** name `rs/k/p`: it is a thin SpawnPK-local wrapper whose
shape does not match the full public `SkyboxPlugin` class.

## Historical-name corroboration

A public RuneLite-derived source preserves a class literally named `Skybox` with the same:

- constructors;
- `ChunkMapper` callback contract;
- parser regex/grammar;
- YCoCg encoding;
- plane override representation;
- Gaussian/error-function blend calculation;
- RGB/HSB conversion;
- BufferedImage render path.

This is stronger than a role-only semantic guess.

## Naming boundary

Exact v308 remains the semantic authority. R91 does not claim whole-source byte identity and
does not name the nested callback or adjacent resource wrapper merely from enclosure.

## Acceptance boundary

Chat 2 does not promote R91. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_69AF0AAE5D5B1F373C29`.
