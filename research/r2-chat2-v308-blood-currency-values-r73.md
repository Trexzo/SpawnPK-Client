# Chat 2 — exact-v308 blood currency value semantics R73

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R73 is a separate non-canonical class-only semantic review batch for the exact per-item
blood-currency value tables used by item hover descriptions.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_33ABFA68EADCBAD63204`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/w` -> `CLIENT_CLASS_000138`
- `rs/d/w$a` -> `CLIENT_CLASS_000139`

## `rs/d/w$a` -> `BloodCurrencyType`

This exact enum preserves three constant names:

- `CORE_TOKENS`
- `DIAMONDS`
- `SHARDS`

Each constant also binds the exact hover icon id and YAML filename:

- CORE_TOKENS -> icon `180`, `blood_core.yaml`
- DIAMONDS -> icon `67`, `blood_diamonds.yaml`
- SHARDS -> icon `68`, `blood_shards.yaml`

Those values are consumed directly by the outer configuration class.

## `rs/d/w` -> `BloodCurrencyValueConfig`

The loader creates one item-id-to-integer map per `BloodCurrencyType`. For every enum
constant it opens the corresponding file under the exact `configs` directory, parses it
with SnakeYAML, and stores each integer item-id/value pair.

The rendering path is equally explicit. When the corresponding hover-description feature is
enabled, the formatter checks the current item id against each table and appends the mapped
value using the surviving format:

` @cya@(<img=<icon>>%,d)`

where the icon comes from the enum.

The Client item-hover path invokes this formatter before the R72 hover-description text is
applied, tying the data directly to item display rather than a generic YAML cache.

That fixes the two identities as `BloodCurrencyValueConfig` and `BloodCurrencyType`.

## Naming boundary

Both names are semantic recovery names. R73 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R73. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_33ABFA68EADCBAD63204`.
