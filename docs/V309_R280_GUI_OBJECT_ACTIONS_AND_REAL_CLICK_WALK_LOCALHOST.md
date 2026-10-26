# SpawnPK v309 R280 — GUI object Search → click-to-walk → localhost movement ACK

**Verified 2026-10-18 in two actual Linux/Xvfb GUI sessions with the previously fully source-built and patched R278 Java11-target client.** Sole integration draft PR #1142, no merge to main. **R280 does not change production Java.**

## New end-to-end acceptance beyond R279

Both real rs.gui.Launcher sessions rendered the 504×335 3D view (>99% nonblack at start and after movement), opened native on-screen context menus with genuine AWT mouse input, emitted **Search Compost heap (ID152)** and **Search Open chest (ID104)** as separate outbound **opcode132/6** requests, and then emitted a *real AWT click-to-walk opcode164* from an open-landscape click at screen (310,315). A localhost test server at **127.0.0.1:43594** separately received ciphertext, independently applied the dummy-login session's ISAAC decoder, validated the object packets, and sent actual inbound **opcode81** player movement to local tile **(46,51)** after decoding the subsequent walk.

| Packet | Server-received wire offset | Authenticated action |
|---|---:|---|
| 132 | 47 | Search Compost heap ID152, world (3201,3202) |
| 132 | 56 | Search Open chest ID104, world (3202,3201) |
| 164 | **65** | Mouse-initiated walk, server ACK local (46,51) |

The real compiled client's **PacketCapture** independently confirmed emitted client packets 132 (twice), outbound walk164 and map-ready121, one original incoming packet60/22 with four cached object spawns (104,114,152,2), two synthetic opcode253 chat responses and the inbound **68-byte opcode81 server placement**.

## Reproducibility

**Replay 1**: existing isolated staged-home test, **exit code 0**. Listener received 74 post-login ciphertext bytes (SHA256 **fe1004c4419494638c6c1831d5fa035e69fb2eff57fa271e6033cbd8b0193ca2**) and decoded object IDs [152,104], then walk at offset65 to (46,51); initial rendered ratio 99.75%, final 99.83%.

**Replay 2**: fully **fresh and separately staged** test home from exact five owner-private SHA-256-pinned inputs, including **10,772 original cache files**. Source-built R278 client SHA pinned before launch. The actual GUI runner returned **exit code 0** and independently reproduced all three actions, world screenshots and scene. Listener again received exactly 74 ciphertext bytes (different SHA256 **05f0d89db9f112dacd91bc0972916e987954c1c8c7a7f7a4312841fb2b38e150**) with the same legitimate object/walk action ordering and local movement ACK. Both runs separately validated that the original early 63-byte object receipt was an exact prefix of the final 74-byte received ciphertext.

An earlier exploratory run already decoded both object packets and walk but exited nonzero because the test reader opened a PNG before the Java Robot finished writing it. It is **excluded** from successful replay counts. The tested R280 Robot now writes PNG to a temporary file and **atomically renames** after complete encoding; the Python wrapper verifies the image is readable. This fixes the harness, **not** the production client.

## Owner-private input hashes

- Original R278 private source-built package ZIP: \`e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280\`.
- Actual patched R278 full class-only JAR: \`dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd\`.
- Original source/dependency R265 ZIP: \`9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb\`.
- User original \`.spawnpk (4).zip\`: \`8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565\`.
- Original client JAR **non-class resources ONLY**: \`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38\`.
- Original resource mapping capsule R230: \`5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125\`.

## Evidence artifact and replay

**One public-safe deterministic evidence ZIP** \`SpawnPK_v309_R280_GUI_TWO_OBJECTS_AND_REAL_WALK_EVIDENCE.zip\`, SHA256 **\`2304aabd0ffaa84b49938b23943cff55ca825bc0d68a5ed77419694cc979d2e0\`**, **1,738,056 bytes**, **44 entries** including SHA-256 manifest. Two independently constructed ZIPs were byte-identical, all entries passed CRC and manifest hashes. Standalone verifier **219/219 assertions PASS**: original decoded server receipts, SHA-pinned ciphertext prefix relation, world positions/ordering, complete client PacketCapture, actual AWT click logs, two independently rendered before/after PNGs for each replay, and proof of fresh archive-to-GUI staging. This ZIP contains independently authored Robot Java, synthetic server + source-derived packet decoders, hash-guarded Linux replay/staging scripts, screenshots and logs, but **NO original/recovered game Java, compiled game JAR, dependency JARs, cache bytes or real account secrets**.

To replay on a capable Linux/Xvfb host, unzip the R280 source-free evidence package and execute:

\`\`\`bash
python scripts/Run-R280-Isolated-GUI.py \
  --r278 /private/R278_FULL_SOURCE_OBJECT_AUTHORITY_GUARDS.zip \
  --r265 /private/R265_UNIFIED_CACHE_PRIVATE.zip \
  --assets '/private/.spawnpk (4).zip' \
  --original /private/client.jar \
  --r230 /private/R230_AUTHENTIC_ASSETS_LOGIN_PRIVATE.zip \
  --output /tmp/r280_new_empty_test_home
\`\`\`

Requires Java JDK11+ with \`javac --release 11\`, Linux Xvfb, Python 3, numpy and Pillow. The script **refuses existing output folders**; no live SpawnPK network or installed owner game is used. Independently validate the source-free ZIP with \`python scripts/tests/R280EvidenceVerifier.py R280_EVIDENCE.zip\`.

**Remaining boundaries:** This confirms real client-originated world-object interactions, a *client click-to-walk*, and a **synthetic localhost** server's authoritative opcode81 reply in one GUI session. It does NOT establish genuine server-side path animation/collision, original NPC/object effects, Cave Entrance ID2 or rotated Cooking range ID114 GUI action selection, native Windows graphics, real server auth, all-region compatibility, or physical power-loss safety. No fresh 1,277-source rebuild was performed in R280; the actual R278 source-built binary is unchanged and pinned. Keep #1142 DRAFT, no merge to main.

**Next R281:** exercise GUI pathing around the Cave Entrance / rotated Cooking range before or after a real object click, and then a native Windows graphical acceptance milestone.
