# Chat 2 — exact-v308 definition config loaders R80

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R80 is a separate non-canonical class-only semantic review batch for five runtime-wired
configuration loaders that build R28 definition objects from the current `configs/*.yaml`
family (or their paired compiled `.bin` forms).

This batch intentionally excludes adjacent `rs/t/a/e` (`maps.yaml`) and `rs/t/a/g`
(`wandering_merchant.yaml`). Their roles are different enough to deserve separate evidence
review rather than being pulled into R80 merely because they share a package.

## Deterministic review result

- candidate classes: **5**
- resolved proposals: **5**
- unresolved: **0**
- review ID: `SEMREVIEW_E585C37C70B2F894E280`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/t/a/a` -> `CLIENT_CLASS_000983`
- `rs/t/a/b` -> `CLIENT_CLASS_000984`
- `rs/t/a/c` -> `CLIENT_CLASS_000985`
- `rs/t/a/d` -> `CLIENT_CLASS_000986`
- `rs/t/a/f` -> `CLIENT_CLASS_000988`

The same ordering reproduces already-reviewed anchors such as `rs/d/a` ->
`CLIENT_CLASS_000110` and `rs/z` -> `CLIENT_CLASS_001125`.

## Shared loader contract

All five classes extend `rs/t/c<T>`, which itself extends the shared file/config support in
`rs/t/a`.

The generic loader selects the YAML source or paired compiled MessagePack source according to
the runtime feature gate, loads an integer-id keyed map, calls the subclass's typed
`a(int, Map)` decoder, stores each typed result in a Trove object map, and exposes lookup
and membership checks used by the corresponding definition system.

## Exact class identities

### `rs/t/a/a` -> `SequenceDefinitionConfigLoader`

Exact sources are `configs/anims.yaml` and `configs/a.bin`. The generic parameter is
R28 `SequenceDefinition`. Its decoder creates or clones sequence definitions, including
sequence/Maya fields, and preserves the diagnostics `(ID {}) Unknown config: {}` and
`Could not find clone ID {} for Anim {}`. Sequence loading invokes this loader and replaces
matching IDs in all active SequenceDefinition arrays.

### `rs/t/a/b` -> `NpcDefinitionConfigLoader`

Exact sources are `configs/npcs.yaml` and `configs/e.bin`. The generic parameter is R28
`NpcDefinition`; keys include `name`, `mapicon`, stand/walk/rotation animations and
retextures. NpcDefinition initialization loads it, and the primary lookup consults it before
the archive-backed path.

### `rs/t/a/c` -> `SpotAnimationDefinitionConfigLoader`

Exact sources are `configs/graphics.yaml` and `configs/g.bin`. The generic parameter is
R28 `SpotAnimationDefinition`; the decoder handles GFX animation, model/render and
recolor/retexture data and preserves `Could not find clone ID {} for GFX {}`. Runtime
spot-animation setup iterates configured IDs and replaces the corresponding definition array
entries.

### `rs/t/a/d` -> `ItemDefinitionConfigLoader`

Exact sources are `configs/items.yaml` and `configs/i.bin`. The generic parameter is R28
`ItemDefinition`; fields include names, model/action data and texture/retexture controls
such as `fulltexture` and `textureinvanim`. ItemDefinition initialization loads it and the
normal lookup returns configured positive IDs before archive decoding.

### `rs/t/a/f` -> `ObjectDefinitionConfigLoader`

Exact sources are `configs/objects.yaml` and `configs/o.bin`. The generic parameter is R28
`ObjectDefinition`; fields include name, actions, models, animation identifiers,
`randomanimstart`, interaction/dimension fields, recolor/retexture data and OSRS mode
selection. ObjectDefinition initialization loads it and the primary lookup checks it before
the ordinary archive/cache path.

## Naming boundary

These are conservative semantic recovery names derived from exact-v308 config identities,
typed outputs and direct runtime consumers. R80 does **not** claim that any proposed name is
a verbatim original SpawnPK developer identifier.

The `ConfigLoader` suffix describes the exact shared runtime contract. It is distinct from
R62's `LegacySequenceConfigLoader` / `LegacySpotAnimationConfigLoader`, which load
`old_a.dat` / `old_g.dat` rather than this current YAML/compiled config family.

## Acceptance boundary

Chat 2 does not promote R80. Main/Core may accept any desired subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_E585C37C70B2F894E280`.
