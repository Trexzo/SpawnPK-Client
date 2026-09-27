# Chat 2 — exact-v308 ConfigDataMapper R248

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/t/a` -> `CLIENT_CLASS_000982` -> `ConfigDataMapper`
- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_015DF1C2D5A96FC35B98`
- field/method proposals: **0**

## Exact-v308 role

The recovered v308 source surface for `rs/t/a` imports both serialization stacks used by SpawnPK config data:

- `org.msgpack.jackson.dataformat.MessagePackMapper`
- SnakeYAML `Yaml`, `DumperOptions`, and `LoaderOptions`

It also carries the bidirectional I/O machinery expected from a shared mapper:

- `InputStream`
- `ByteArrayOutputStream`
- `FileOutputStream`
- `FileWriter` / `Writer`
- `Files` / `OpenOption`
- `TypeReference`
- `Map`, `List`, `HashMap`, `AbstractMap`
- `ToIntFunction`

R247 `DefinitionConfigLoader` extends this exact class, placing it beneath the reviewed definition-loader family.

Separately, the exact-v308 asset-authoring validation successfully exercised the same MessagePack config path when reading a generated item configuration, corroborating that this subsystem is the real runtime config mapping stack rather than dead tooling.

## Naming boundary

`ConfigDataMapper` is deliberately descriptive.

It expresses the proven shared YAML/MessagePack mapping role without claiming that the original unobfuscated source used this exact identifier.

Confidence: **0.995**.

## Acceptance boundary

R248 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
