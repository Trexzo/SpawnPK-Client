# Chat 2 — exact-v308 shader exception / texture manager R90

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R90 is a separate non-canonical class-only review batch for two remaining R87/R89-adjacent
GPU classes with exceptionally strong exact-v308 and public RuneLite-derived identity
corroboration.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_68277D6628CE7C514BD0`
- field/method proposals: **0**

## Stable IDs

- `rs/k/n` -> `CLIENT_CLASS_000344` -> `ShaderException`
- `rs/k/q` -> `CLIENT_CLASS_000348` -> `TextureManager`

## `rs/k/n` -> `ShaderException`

Exact v308 is a minimal exception class:

- extends `java.lang.Exception`;
- owns one constructor `(String)`;
- delegates directly to `Exception(String)`.

R89 `Shader` constructs and throws this exact class for its shader/program failure
surface:

- shader object creation failure;
- shader compile failure using the OpenGL info log;
- program link failure using the program info log;
- program validation failure using the program info log.

A public RuneLite-derived GPU source preserves `ShaderException` with the identical
superclass and constructor contract.

The class identity is therefore stronger than a generic inferred exception noun.

## `rs/k/q` -> `TextureManager`

Exact v308 owns the GPU texture-array lifecycle.

The class has the exact texture size constant:

`128`

and constructs a `GL_TEXTURE_2D_ARRAY` with:

- eight mip levels;
- `GL_RGBA8` storage;
- 128 x 128 layers;
- one layer per client texture.

It verifies that all texture pixels are available before creating the array, temporarily
sets the texture provider brightness to `1.0` so the GPU receives unmodified textures,
converts integer RGB pixels into direct RGBA byte buffers, uploads each layer, restores the
prior brightness and generates mipmaps.

It also owns:

- mipmap enable/disable behavior;
- anisotropic filtering clamped to the GL-reported maximum;
- texture-array deletion;
- per-texture animation vectors derived from animation direction and speed.

The upload path preserves the exact diagnostic:

`Uploaded textures {}`

A public RuneLite-derived `TextureManager` preserves the same 128 texture size, texture
array allocation, brightness handling, pixel conversion, anisotropic filtering, mipmap
generation, animation-vector computation and diagnostic.

## Naming boundary

These names are backed by exact-v308 behavior and direct R89/R87 consumers plus matching
public RuneLite-derived identities.

Exact v308 remains the authority. R90 does not imply whole-source byte identity or promote
either name canonically.

## Deliberate exclusions

R90 does not pull in the remaining `rs/k/*` helpers merely because the GPU family is now
well understood. Compiler switch maps, thin runnable wrappers, generic matrix helpers and
the `skybox.txt` family remain separate evidence questions.

## Acceptance boundary

Chat 2 does not promote R90. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_68277D6628CE7C514BD0`.
