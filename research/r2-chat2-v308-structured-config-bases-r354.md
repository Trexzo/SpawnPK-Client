# Chat 2 — structured config bases R354

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/t/a` -> `CLIENT_CLASS_000982` -> `StructuredConfigStore`
- `rs/t/c` -> `CLIENT_CLASS_000993` -> `DefinitionConfigMapper`
- review: `SEMREVIEW_5D7E2450563CF7116F3A`

## StructuredConfigStore

The base owns two paths:

- human-editable structured config;
- compiled binary config.

It loads the former through SnakeYAML and the latter through MessagePackMapper, both into:

`Map<Integer, Map<String,Object>>`

It can also write the structured map back to YAML.

Direct exact-v308 users include map-region overrides, wandering-merchant config and the typed
definition mapping hierarchy.

## DefinitionConfigMapper

`rs/t/c<T>` extends that store and adds:

- typed int-keyed cache of T;
- abstract per-id mapper `T a(int, Map<String,Object>)`;
- materialization lifecycle that maps every config record into T;
- reusable conversion helpers for primitive arrays / nested arrays / string arrays.

Concrete exact-v308 subclasses map into:

- animation definitions;
- NPC definitions;
- spot-animation/GFX definitions;
- item definitions;
- object definitions.

## Boundary

These are storage/mapping abstractions only. They do not imply server gameplay authority.

R354 remains non-canonical semantic research only.
