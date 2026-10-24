# v309 R277 — actual mixed object models, collision footprints, route rejection, and short GUI chest check

**2026-10-18. Single active SpawnPK-Client owner; integration PR #1142 stays DRAFT.** No production source change from the R274 one-file stale-object guard; no main merge, no Windows installed client modification. Owner original cache/JAR and reconstructed proprietary source remain private.

## 227/227 new clean-room tests PASS, 115/115 previous R276 regression rerun PASS

The R277 private-input-hash-pinned Linux runner independently staged the exact owner's R274 full Java11-target source-built class-only JAR (SHA256 \`09920fc5db420f384a43a267ca6d976df49b8a587c8dde8d1c77b47ab8b416b4\`), source-built R265 dependency capsule (ZIP SHA256 \`9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb\`), and exact original \`.spawnpk (4).zip\` cache (SHA256 \`8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565\`). Java test compiled using \`javac --release 11\` in a new temp workspace; no in-place owner edits.

It invokes actual compiled \`Client.method2310\` nested object151/101 decoder, \`Client.method1808\` pending-object promotion, original \`ObjectDefinition\`, authentic \`OsrsModelCache\`, real \`Scene\`, real \`CollisionMap\`, real \`Client.method3573\` walk route, and R274 real \`handleMenuAction(62)\` stale-hash guard. Actual OSRS models loaded, not synthetic:

| Real cache object | ID | OSRS model | Size | Vertices / faces |
| --- | ---: | ---: | --- | ---: |
| Cave Entrance | 2 | 731 | **4×2** | **88 / 157** |
| Cooking range | 114 | 5274 | **1×2**, rotated orientation1 → **2×1** | **146 / 193** |
| Compost heap | 152 | 1428 | **2×2** | **32 / 42** |
| Open chest | 104 | 1226 | **1×1** | **152 / 286** |

All four queue independently and enter real Scene with genuine packed identities when model-ready. Collision occupancy confirmed across **every tile** in the 4×2 cave, 2×2 heap, rotated 2×1 range, and 1×1 chest; removal/restore of the range swaps collision from 2×1 to 1×2 with no ghost bits or disturbed neighbors. Actual source pathfinder **refuses** exact-target routes into 4×2 cave and 2×2 heap; no forbidden opcode164 is emitted. Cave removal frees the former 4×2 area and permits an actual outgoing walk route. Its old positive scene hash is rejected for item-on-object by R274's production guard. Remaining objects reverse-remove with all collision bits clear.

**Actual compiled Java checks 189/189 PASS**. Separate standalone strict opcode60/151/101 framing across four distinct object IDs, variable orientations, ordered remove/reinsert, declared sizes, and malformed/ambiguous bytes **38/38 PASS**. Combined in exact checksum-guarded disposable-home runner **227/227 PASS**. The previous R276 83 Java +32 codec checks were also fully **re-executed 115/115 PASS** in a separate fresh temp home; R274 316-suite remains historical and was NOT rerun this batch.

## Limited real GUI check — short interaction; no sustained acceptance

A separate actual Linux/Xvfb graphical replay, with original non-class UI resources and owner's local-only cache, reached a rendered view and a real **Search Open chest** context menu. Isolated \`127.0.0.1:43594\` server sent **one 22-byte opcode60 packet with FOUR distinct object151 spawns**: chest104, cave2, range114 rotated, compost152. Actual Client packet capture confirmed receipt of 60/22. A real AWT mouse-click selected Search; client emitted opcode132/6. Separate mock listener independently ISAAC-decoded opcode132 **object104** at world (3202,3201), byte offset **42**, after receiving map-ready121. Synthetic opcode253 \`Chest: The lid creaks open.\` sent in response.

**Important:** session reported peer closure after **10.61 seconds**, and the graphical driver did not complete its longer observation before timing out. This is **not** a sustained GUI pass or proof that cave/range/heap are all visibly rendered/pickable. The on-screen context menu and chest packet are proven only; native Windows GUI, original loot/dialogue, interaction with the three other IDs, genuine server login/gameplay remain unverified. A complete early action wire capture is 49 bytes; the later final server receive stream is 52 bytes. Both are included separately to avoid confusing different capture horizons.

## Reproducible owner-private evidence ZIP

\`SpawnPK_v309_R277_MIXED_OSRS_OBJECT_COLLISION_EVIDENCE.zip\` SHA256 **\`2a151574136c3add9cef3eabf39b73a1306cbd99cd69f977bfb572d35fc6dd18\`**, **268,317 bytes**, **29 entries**. Two independent package builds yielded identical bytes, all CRC/size/SHA manifests verified. Independent archive/evidence validator **117/117 PASS**, including actual decompression and pixel analysis of genuine GUI screenshot: viewport **97.94% nonblack**. Contains 189-check actual-client standalone Java regression source, 38-check Python codec, re-executed R276 logs, exact SHA-pinned isolated Linux runner, **untested native Windows PowerShell** runner, short synthetic GUI probe sources, exact dual-horizon client and server ciphertext receipts, screenshot and full manifest. NO proprietary original game Java, JARs, original cache files or secrets.

**Next R278:** validate multiple distinct on-screen object picks, rotated footprint / occupied-tile mouse pathing against the *actual loaded landscape* over a sustained localhost session. Separately native Windows GUI acceptance. Preserve private source provenance and keep sole PR #1142 DRAFT, no main merge.