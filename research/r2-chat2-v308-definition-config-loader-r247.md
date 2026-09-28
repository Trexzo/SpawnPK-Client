# Chat 2 — exact-v308 DefinitionConfigLoader R247

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/t/c` -> `CLIENT_CLASS_000993` -> `DefinitionConfigLoader`
- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_49C5746CC69F9B4CED9D`
- field/method proposals: **0**

## Exact-v308 role

`rs/t/c<T>` is an abstract generic subclass of `rs/t/a`.

It owns:

- an int-keyed cache of materialized `T` definitions;
- the raw `Map<Integer, Map<String,Object>>` config corpus;
- the YAML-vs-compiled loading mode.

Its reload method clears both stores, reads the source through the parent YAML/MessagePack loader, then visits every integer ID and calls the abstract:

`T a(int, Map<String,Object>)`

to materialize the concrete definition.

It also exposes:

- lookup by integer ID;
- presence testing;
- access to the typed cache;
- common scalar/array conversion helpers used by definition decoders.

## Family proof

The already reviewed R80 classes all extend this exact superclass:

- `SequenceDefinitionConfigLoader`
- `NpcDefinitionConfigLoader`
- `SpotAnimationDefinitionConfigLoader`
- `ItemDefinitionConfigLoader`
- `ObjectDefinitionConfigLoader`

Those subclasses bind concrete definition types and exact YAML/compiled config files, so `DefinitionConfigLoader` is a conservative semantic identity for their shared generic loader.

This does **not** claim a verbatim original developer identifier.

## Acceptance boundary

R247 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
