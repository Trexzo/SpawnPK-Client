# SpawnPK v309 — R268 actual rendered world and local player

**Sole active SpawnPK-Client chat; continuation of R267.** Client production source and its integrated cache-R246 helper are **unchanged**. Public files contain independently authored diagnostics and documentation only.

## Runtime result (real GUI, Linux Xvfb, 2026-10-17)

Using the actual R265 **source-built Java 11-target** diagnostic client, archived original nonclass UI resources, and the original owner \`.spawnpk (4).zip\` cache staged into a disposable home, I reproduced actual game terrain and a locally rendered player on the real \`rs.gui.Launcher\` client.

**Bug in former synthetic server fixture:** opcode 249 (local player identity) + opcode 73 (region 400,400) + minimal opcode 81 (appearance-only type0) left \`localPlayer.pathX/Y=(-3152,-3152)\`. Even R267's genuine 264-vertex / 472-face mesh cannot render on screen with the local player outside the scene. This was an isolated **test protocol omission**, not a confirmed production client rendering defect.

**R268 correction:** initial opcode 81 has bitstream fields \`[update=1:1bit, type=3:2bits, plane=0:2bits, teleport=0:1bit, needsAppearance=1:1bit, y=48:7bits, x=48:7bits, otherCount=0:8bits, sentinel=2047:11bits]\` = **five bytes**, then \`0x10\` appearance mask, negated length byte, and 61-byte real IdentityKit body = **68-byte frame**. Actual diagnostic logs:

\`\`\`
R265_SELF_MASK_BEFORE mask=16 appearance=false position=48,48 packetCaret=6
R265_SELF_MASK_AFTER mask=16 appearance=true position=48,48 packetCaret=68
R265_PLAYER_SYNC_DONE localPlayer=true appearance=true selfUpdates=1 caret=68/68
\`\`\`

Live Xvfb screenshots show a character, ground, fence, trees, tent/buildings, minimap and complete HUD. Pixel inspection in screen viewport (504×335):

| Fixture | Nonblack pixels | Ratio |
|---|---:|---:|
| Earlier R268 appearance-only, invalid position | 1,062 / 168,840 | 0.63% |
| Correct type3 local teleport | 168,411 / 168,840 | 99.75% |
| Independently restaged clean home | 168,384 / 168,840 | 99.73% |

The clean-home runner hash-verifies original archives, stages 10,772 files / 209,747,201 bytes in its own test home and uses localhost-only TCP. Screenshot ZIP includes exact images and logs.

**Actual Java regression:** \`tests/java/r268/R268TeleportAppearanceRegression.java\` compiles \`--release 11\` against the pinned source-built R265 private production JAR and invokes real \`Client.method1850\` with two authentic-bit-layout teleport/appearance packets. **63/63 assertions PASS**; repeat unmasked sync and teleport to tile (50,49) retain appearance; truncated body fails.

**Session-liveness improvement:** Reading the actual client revealed \`field808 > 750\` triggers reconnect without incoming frames. The repaired mock server emits unchanged 3-byte opcode-81 frames every approximately 2.5 seconds. The real client decoded **eight** such updates (nine synchronizations including initial) and held a **26-second post-login loopback session observation window**. It later reconnects after the test server closes, so indefinite gameplay is NOT proven.

## Pinned inputs

- R265 private full-source ZIP SHA256 \`9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb\`
- R265 real source-built production JAR SHA256 \`dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503\`
- R265 diagnostic JAR SHA256 \`ece94b2f5a49e8d2a07dcbe97c0456caa9618f801c77ae929a1a99a7e5b2a59a\`
- Original archived client resource input SHA256 \`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38\` (non-class resources only)
- User \`.spawnpk (4).zip\` SHA256 \`8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565\`
- R230 resource-mapping package SHA256 \`5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125\`

**Verified private-source-free evidence ZIP:** \`SpawnPK_v309_R268_REAL_RENDERED_WORLD_LOCAL_PLAYER_EVIDENCE.zip\`, **SHA256 \`ae4f7fe7e5751943936d909ef42bdef32e195801a2a6684014f45c2bc5ba321f\`**, 647,434 bytes, 23 entries, manifest 22 hashed files, CRC and runner replay verified. Includes screenshots, synthetic localhost probe, hash-guarded staging, Linux GUI runner, Windows protocol-only runner and logs. No proprietary original client source, asset ZIP, code JAR or dependencies included.

## Remaining gates

- **Not live-server playable**, no genuine server authentication, NPCs, interactions, combat, pathing or fully sustained gameplay.
- Opcode 121 map-ready reception was **not confirmed in these R268 captures**; earlier R264 independently observed it. Do not extrapolate R264's map-ready receipt to R268.
- The original binary and asset cache are from different revisions; the success validates the tested scene and selected model assets, not all game areas or data.
- No fresh R268 complete private source rebuild; test compiled against R265's previously verified production JAR. Native Windows GUI and Windows PowerShell runner NOT executed. No original-bytecode parity or power-loss acceptance.

**GitHub:** keep this PR and historical #1084 / #1141 **DRAFT**; no merge to \`main\`. The next stage should extend the localhost world protocol, verify outbound ISAAC/121 under the latest fixture and test real movement/interactions before owner-local Windows acceptance.
