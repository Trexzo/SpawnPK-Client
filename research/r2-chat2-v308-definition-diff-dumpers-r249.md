# Chat 2 — exact-v308 definition diff dumpers R249

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/t/b/a` -> `CLIENT_CLASS_000991` -> `NpcDefinitionDiffDumper`
- `rs/t/b/b` -> `CLIENT_CLASS_000992` -> `ItemDefinitionDiffDumper`
- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_B3DC93033FB5AD7BD2B7`
- field/method proposals: **0**

## Exact behavior

`rs/t/b/a` compares NPC definitions (`rs/d/d`) field-by-field, carries the surviving diagnostic `Found differences in NPC ...`, writes changed properties through the shared config mapper into `e.yaml` / paired `e.bin`, and has a second inspection path using the reviewed `NpcDefinitionConfigLoader`.

`rs/t/b/b` performs the corresponding item-definition (`rs/d/k`) comparison, carries `Found differences in item ...`, writes changed properties to `i.yaml` / paired `i.bin`, and its verification path loads the reviewed `ItemDefinitionConfigLoader` after printing `Running test..`.

Both dump paths finish with the exact marker `..Dump completed!`.

## Naming boundary

The `DiffDumper` suffix is deliberate: these classes compute changed fields relative to another definition source instead of merely serializing whole definitions.

These are conservative semantic recovery names, not claims of verbatim original developer identifiers.

## Acceptance boundary

R249 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
