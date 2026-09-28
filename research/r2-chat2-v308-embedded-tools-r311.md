# Chat 2 — exact-v308 embedded definition/debug tools R311

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/l/b/a/b/b` -> `CLIENT_CLASS_000375` -> `TextureDebugConfigLoader`
- `rs/t/b/a` -> `CLIENT_CLASS_000991` -> `NpcDefinitionDumpTool`
- `rs/t/b/b` -> `CLIENT_CLASS_000992` -> `ItemDefinitionDumpTool`
- review: `SEMREVIEW_730D656BFB9058CF080B`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 evidence

### Texture debug configuration

`rs/l/b/a/b/b` creates `./debug` when necessary and opens `./debug/textures.txt`. It clears six integer lists, skips `#` comment lines, recognizes `[textur]`, `[random]`, and `[recolor]` section markers, and parses comma-separated integer entries according to the active section.

### NPC definition dump tool

`rs/t/b/a` walks NPC definition slots and compares the current `rs/d/d` definitions to baseline/template definitions. Its difference map covers name, combat level, actions, models, recolors/retextures, chat-head models, animations, scale, minimap/priority rendering, head icon, pet/clickable state and related fields.

The exact bootstrap/string contract contains **Found differences in NPC**, **..Dump completed!**, and generated **e.yaml / e.bin** output names.

### Item definition dump tool

`rs/t/b/b` performs the parallel operation for `rs/d/k` item definitions. Its comparison surface includes item name/note/template/clone state, actions and ground actions, stacks, model and 2D transforms, recolors/retextures, resize, worn/chat models, ambient and contrast.

Exact strings include **Found differences in item**, **..Dump completed!**, **Running test..**, **..Test completed!**, plus generated **i.yaml / i.bin** outputs and an embedded **Dwarf remains** item fixture.

## Global-authority preflight

Unlike the discarded duplicate attempt, R311 was checked against the complete class-owner/name/stable-ID authority: the R2 seed plus R3-R310 review batches. All three owners, names, and stable IDs are new.

## Boundary

R311 remains non-canonical semantic research. The names describe exact-v308 roles and do not claim original stripped developer identifiers.
