# Chat 2 — exact-v308 legacy item-definition config parser R79

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R79 is a separate non-canonical class-only semantic review batch for a surviving legacy
item-definition configuration parser.

Unlike the recent runtime-wired batches, no direct exact-v308 caller of this class survives.
The proposal therefore carries confidence **0.997**, not 0.999, and makes no claim that this
path is active in production.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_A5BA60F6DC0C2915E066`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/g` -> `CLIENT_CLASS_000117`

## `rs/d/g` -> `LegacyItemDefinitionConfigParser`

The class derives one exact source path from the client cache/config root:

`configs/old_i.dat`

One method reads that file line-by-line into a static raw-line list when its feature gate is
enabled.

The parsing method recognizes exact `[item ...]` blocks and a broad legacy item-definition
grammar. Surviving keys include, among others:

- `name`
- `modelid` / `groundmodel`
- `clone`
- `description`
- `zoom`
- `offset1` / `offsetx`
- `offset2` / `offsety`
- `value`
- texture ids/colors/flags
- male/female equipment/model fields
- actions
- stack ids/amounts
- `certid` / note
- `template`
- `stackable`

Each parsed block creates or clones an R28 `ItemDefinition`, mutates those ItemDefinition
fields directly, and inserts the result into an item-id keyed Trove object map.

The parser also preserves the exact diagnostic:

`Error! Detected mismatch at line: <n>`

These facts are sufficient to identify the class as a legacy item-definition config parser,
but not to assert active runtime use.

## Naming boundary

`LegacyItemDefinitionConfigParser` is a semantic recovery name. R79 does not claim it is a
verbatim original SpawnPK developer identifier or an active production loader.

## Acceptance boundary

Chat 2 does not promote R79. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A5BA60F6DC0C2915E066`.
