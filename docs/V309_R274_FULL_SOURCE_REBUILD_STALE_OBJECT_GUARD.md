# v309 R274 — complete Java11-target rebuild, stale-object guard, original OSRS chest geometry

**2026-10-18, sole active client chat. DRAFT ONLY.** Builds the actual owner-private R265 Java source snapshot (cache-R246 integrated), changing **only one existing source file**. The full derived source and production JAR **remain private**; only standalone test descriptions and a source-free evidence validator live on GitHub. Do not merge main or install into the owner's native Windows setup without acceptance.

## Production change: actual missing-scene-object authority guard

In \`Client.handleObjectClick\`, the original code retrieves \`n5 = Scene.getHashAtTile(planeLevel, tileX, tileY, suppliedPackedHash)\` but mistakenly rejects only \`suppliedPackedHash == -1\`. With a **positive, stale/forged packed hash**, \`n5 = -1\` was ignored and real item-on-object could still emit **opcode192** even though the scene object was absent.

The R274 private patch adds the missing lookup-result guard: reject when **either** \`suppliedPackedHash == -1\` **or** \`n5 == -1\`, before navigation/packet creation. Does not alter valid \`Search (502 → 132)\`, \`Shut (900 → 252)\`, or valid item-on-object behavior.

**Red/green evidence:** original R265 class JAR fails exact missing-scene guard assertion while emitting stale action; patched R274 full-source-built JAR passes **39/39 original real scene/menu checks**, including rejection of bogus scene lookups and retention of valid actions. Full private source preimage and patched postimage:
- \`source/rs/Client.java\` R265 SHA256 \`13a7c5a386112c9ca122fd8557dfca0a77e024de8e29a203d205528b1e88fc9d\`
- R274 changed Client.java SHA256 \`1c3ca60ede6973d92eaf277471db2659dad024c19c15a85472fda90e63dd5201\`
- All other **1,276** source files preserved byte-for-byte.

## Major build milestone — source compilation achieved

JDK21 \`javac --release 11 -proc:none -g:none\` processed **all 1,277 Java files** and emitted **1,386 compiled classes, zero errors**. Previous R273 full compile failed because obfuscated third-party class names conflict with package names (for example \`gnu.trove.f\` vs \`gnu.trove.f.b.cc\`). R274 uses a **compile-only filtered copy** of the exact R239 JAR that suppresses eight Java class/package namespace collisions:
\`gnu/trove/{e,e/a,f,f/b,i,i/a}.class\` and \`com/google/c/{a,c}.class\`. The original R265 archives, compiled runtime dependencies, actual cache and installed client were **not** mutated. The same 1,277-source rebuild from a fresh hash-verified source extraction independently reproduced the **exact same deterministic class-only JAR**.

**Private R274 source-built class JAR SHA256** \`09920fc5db420f384a43a267ca6d976df49b8a587c8dde8d1c77b47ab8b416b4\`. Uses actual source-built classes only; external existing private runtime dependencies/UI resources are still required for native launching. Release-target bytecode is Java 11.

## Eight actual rebuilt-client test suites: 316/316 assertions PASS

| Suite | Checks |
|---|---:|
| Actual Client scene/guard and chest Search/Shut/item-use | 39 |
| Authentic OSRS model1226 + direct \`Scene.method1653\` insert | 21 |
| Original inbound object subpacket151 queue decode | 12 |
| Actual NPC menu action wire encoders | 64 |
| Original NPC definition + inbound spawn + Talk-to | 19 |
| Actual route/ISAAC walk opcode164 + direct server-style ACK | 23 |
| Authentic seven-kit actor mesh/appearance | 75 |
| Actual player teleport/appearance opcode81 | 63 |
| **Total** | **316** |

Both the initial full build-directory classes **and** the deterministic 1,386-class JAR passed all eight suites independently.

## Original chest ID104 model readiness and scene insertion

Actual \`Open chest\` definition ID104 names model **1226**; \`ObjectDefinition.method2285()\` selects the **OSRS** model cache. Loading model1226 from the owner's exact \`.spawnpk/main_file_osrs.dat\` + \`main_file_osrs.idx1\` (not \`main_file_cache.dat\`) produces a real **152-vertex, 286-face** mesh. \`ObjectDefinition.method197(10)\` reports ready after registering it in the correct OSRS model-header bank. Actual \`Scene.method1653\` accepts that nonempty mesh, tile (50,49), and authentic packed hash \`1075452082\`; subsequent real \`Scene.getHashAtTile\` resolves it. This is **offline direct source-backed insertion**, not proof of automatic scene promotion or real GUI mouse picking.

## GUI boundary — still unresolved

A separate diagnostic-only graphical replay using the rebuilt source did **not** attain stable rendered login/world state within the controlled test period; its mock listener eventually logged a broken pipe. The captured partial \`graphicsMode=1\` trace cannot establish object visibility, object click opcode132, or server reply. No such runtime acceptance is claimed. The new production fix addresses only stale scene lookups; it does **not** magically make a missing chest appear.

## Source-free public vs owner-private output

One private package \`SpawnPK_v309_R274_FULL_SOURCE_REBUILD_STALE_OBJECT_GUARD.zip\`, **SHA256 \`8a943daba9dfe4b97d4e314d818d9eaa4405c4583ab5726f4411dac2f09675d2\`**, 2,402,547 bytes, **24 ZIP entries**. Independently rebuilt twice with byte-identical archive SHA, all CRC and per-entry hashes PASS, and portable evidence regression **79 assertions PASS**. It includes the private class-only JAR, one-file guarded diff, exact-hash \`rebuild_r274.py\` and PowerShell wrapper, eight independently authored Java tests, expected-red/actual-green logs, complete javac and suite logs, and diagnostics. **Do not commit this ZIP, source patch full context or compiled private JAR publicly.**

User's original R265 archive SHA256 \`9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb\`. Owner asset ZIP SHA256 \`8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565\`.

**Next R275:** instrument actual client pending-object queue and OSRS model-loader/scene promotion after a *confirmed fully rendered* GUI session, test AWT selectable chest → emitted/independently received opcode132 → synthetic response253; separately perform native Windows JDK GUI acceptance. Keep PR #1142 DRAFT; no merge to main, no real authentication/combat or original-bytecode parity claimed.
