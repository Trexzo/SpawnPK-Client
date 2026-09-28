# Chat 2 — exact-v308 OSRS scanner override loaders R100

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R100 is a separate non-canonical class-only review for the two definition-override adapters
owned directly by the readable exact-v308 `OsrsMapDependencyScanner`.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_F3C13FDAE984E6075BB8`
- field/method proposals: **0**
- confidence: **0.997** each

## Stable IDs

- `rs/cache/osrs/util/a` -> `CLIENT_CLASS_000107` -> `OsrsSequenceOverrideLoader`
- `rs/cache/osrs/util/b` -> `CLIENT_CLASS_000108` -> `OsrsObjectOverrideLoader`

## OsrsSequenceOverrideLoader

The class extends R80 `SequenceDefinitionConfigLoader`.

Its scanner-owned load path:

1. obtains the source/config root from `OsrsMapDependencyScanner`;
2. resolves `configs/anims.yaml`;
3. parses that YAML through the scanner's YAML reader;
4. clears the inherited typed sequence-definition map;
5. iterates every configured sequence ID;
6. decodes each entry through the inherited exact sequence-definition decoder;
7. repopulates the scanner's override map.

This is not the normal runtime config-loader path. It is the scanner-specific adapter that
lets the exact diagnostic tool use client animation overrides while auditing OSRS map
dependencies.

The scanner's own report text states explicitly:

`Uses client object/animation overrides and configs/*.yaml, not serialized production configs.`

## OsrsObjectOverrideLoader

The class extends R80 `ObjectDefinitionConfigLoader`.

It resolves:

`configs/objects.yaml`

from the same scanner-owned source root and rebuilds the inherited object-definition map.

The scanner adapter applies additional exact policy that the normal runtime loader does not:

- ordinary non-OSRS entries are skipped;
- entries marked `osrs` are included;
- entries carrying revision-forcing metadata are also included;
- the active ObjectDefinition mode is switched between OSRS and ordinary modes;
- the corresponding pair of definition byte arrays supplied by the scanner is installed
  before decoding;
- configured IDs outside the active definition table fail closed with the
  `Object override outside definition table` diagnostic family.

This fixes the role as the OSRS-map scanner's object-override adapter rather than another
generic ObjectDefinition loader.

## Naming boundary

Neither obfuscated adapter retains a historical public source noun.

The names are therefore deliberately descriptive:

- `OsrsSequenceOverrideLoader`
- `OsrsObjectOverrideLoader`

Exact v308 proves their owner, config resources, definition types and scanner-only policy.
Confidence is 0.997 rather than 0.999 because the English class nouns are recovered roles,
not surviving developer identifiers.

## Acceptance boundary

Chat 2 does not promote R100. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F3C13FDAE984E6075BB8`.
