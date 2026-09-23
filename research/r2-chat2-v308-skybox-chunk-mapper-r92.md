# Chat 2 — exact-v308 Skybox ChunkMapper R92

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R92 is a separate non-canonical class-only review batch for the nested callback contract
consumed directly by R91 `Skybox`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_495C2BF2A1DABD1F125D`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/k/o$a` -> `CLIENT_CLASS_000346`

## `rs/k/o$a` -> `ChunkMapper`

Exact v308 defines `rs/k/o$a` as a public interface with exactly one method:

`int a(int, int, int)`

R91 `Skybox` accepts that interface in its internal chunk-data lookup and therefore in the
public color-sampling/rendering paths.

When a mapper is supplied, Skybox passes:

- chunk X;
- chunk Y;
- plane

to the callback.

A return value of `-1` means there is no mapped template chunk. Otherwise the returned
packed integer is decoded as:

- template chunk Y from bits 3..13;
- template chunk X from bits 14..23;
- template plane from bits 24..25.

Skybox then samples its configured skybox data using those mapped coordinates.

## Historical-name corroboration

The matching public RuneLite-derived `Skybox` declares:

`@FunctionalInterface public interface ChunkMapper`

with the single contract:

`int getTemplateChunk(int cx, int cy, int plane)`

and consumes it in the same chunk-data, color-sampling and render paths.

The owner relationship, arity, return type and exact packed-template semantics therefore
support the nested semantic identity `ChunkMapper` independently of mere enclosure.

## Naming boundary

Exact v308 remains the semantic authority. R92 names the class/interface only; it does not
propose a method semantic name, because post-R2 method proposals remain outside the current
class-research expansion.

## Acceptance boundary

Chat 2 does not promote R92. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_495C2BF2A1DABD1F125D`.
