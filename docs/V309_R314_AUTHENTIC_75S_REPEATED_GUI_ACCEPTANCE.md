# R314 — sustained authentic v309 recovered-client world session and late interaction

**26 October 2026.** Owner-private complete recovered-source v309 client, on [Draft PR #1143](https://github.com/Trexzo/SpawnPK-Client/pull/1143). Separate v311 original bytecode recovery is untouched.

## Why this matters

R313 demonstrated only 28–30.3 seconds of authentic asset-backed Linux/Xvfb GUI and local protocol interaction. Its test script deliberately ended at 30 seconds, and its bounded local server had a 50-second lifetime. R314 extends **only the owner-private test harness**, not production Java or its binary, and demands real GUI responsiveness after 55 seconds, plus continued rendering and a live local server at 75 seconds.

### Unchanged authentic inputs

- Original owner cache (10,772 files, 209,747,201 extracted bytes) ZIP SHA-256: `8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565`.
- Original v309 resource-only JAR source SHA-256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Original R265 recovered-source archive SHA-256: `9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb`.
- Original R230 mappings archive SHA-256: `5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125`.
- Source-compiled production JAR SHA-256 unchanged from R311 through R314: **`b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`**.

The original client JAR was used only to stage resource data, not as an executable game-code fallback. Asset extraction selectively uses `.spawnpk/`; unrelated `.spawnpk-data/` content is excluded. The test does not use real accounts or contact the live SpawnPK service; game server bound **127.0.0.1:43594** with explicitly inert synthetic login.

## Two independent full GUI replays

Real recovered-client `rs.gui.Launcher`, Java/AWT GUI at 1400×900 Linux/Xvfb, original cache-backed region **13386 (field1134)**, visible terrain, local actor, minimap, and nearby interactive scene objects. Both runs used the **unchanged** source-built game JAR and genuinely executed Java Robot mouse clicks.

| Evidence | Initial 75s run | Fresh packaged-runner replay |
|---|---:|---:|
| Main fixture process exit | 0 (PASS) | 0 (PASS) |
| Verified alive at final checkpoint | 75.20 s | 75.17 s |
| Recorded 81 heartbeat emissions | 24 | 23 |
| Screenshot checkpoints | 40, 55, 70, 75 s | 40, 55, 70, 75 s |
| Actual mouse-driven Cook actions | 2 | 2 |
| Second Cook acknowledgment | at 58.21 s | at 58.14 s |
| ISAAC decoded action | opcode 132, object 114 | opcode 132, object 114 |
| Original world tile | (3362, 4769) | (3362, 4769) |
| Local server response | opcode 253, both actions | opcode 253, both actions |
| Captured client outgoing wire | 104 bytes | 102 bytes |
| Wire SHA-256 | `68b51bae1d1dd17bcb2f5f6d0be10a5478c97b248d482fa976cd07fa02cf0b99` | `3e343d251a787aebb671d14e87c80bd81350d54ebe56d99c7c97d95b69b1d95a` |

The client and local server were alive at every screenshot; 75-second screenshot viewport nonblack ratio about **0.985**, with all fixture child processes cleanly terminated. The distinct wire lengths and hashes reflect separate authentic executions; they are not falsely treated as byte-identical packet streams.

**Real responsiveness evidence**: after an already-rendered >55-second session, the real Robot opened the object's in-game context menu and clicked Cook again. The client emitted a second distinct ISAAC-decoded 132 packet, verified with object/tile identity and a separately decoded local opcode253 server acknowledgment. This is stronger than process liveness alone.

## Source build, inherited suite and delivery

- All **1,277 original recovered Java sources** compiled successfully with `javac --release 11` into **1,386 classfiles**, reproducing the **exact same** SHA-256 pinned R311 client JAR.
- All **2,703/2,703** previous real compiled-client offline regression assertions PASS on the cumulative R314 package: R308 256; R309 38; R310 15; R311 37; R312 2,357.
- Fresh cumulative private ZIP `SpawnPK-v309-R314-Full-Recovered-Source-Private.zip`, **23,373,090 bytes**, SHA-256 **`360c1feb94d383dd3dcdf2f2c43740eed59ca274409a3b91ad1ed7c921da263f`**, includes all recovered Java source, dependencies, unchanged class-only JAR, offline regression/build tools, R314 reproducible SHA-pinned authentic-cache GUI test fixture and sanitized original/packaged run receipts with screenshots. Original 203 MB cache archive, original client resource JAR, original source inputs, account data and production session material are NOT bundled. The private archive is shared only with its owner, **not uploaded to GitHub**.
- The packaged runner re-staged the original SHA-pinned inputs into a fresh isolated test home and independently achieved the second 75.17 s PASS with top-level exit **0**.

## Remaining acceptance gates

This is a real 75-second local synthetic-server session, **NOT** authenticated public SpawnPK gameplay, multi-hour operation, general PvP/PvE feature coverage, a full multi-minute soak, or owner-native Windows GUI/NTFS/GPU acceptance. Original data/assets came from owner-private archives and no personal credentials were used.

**Keep PR #1143 DRAFT and UNMERGED.** R314 is a **test-harness-only** milestone; production code remains the accepted R311 baseline. Do not publish private recovered source/binaries or misstate public CI as the original game acceptance.
