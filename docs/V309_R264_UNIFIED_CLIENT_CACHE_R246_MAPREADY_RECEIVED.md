# R264 — sole-owner client integration: R247 + cache R246, map-ready 121 decoded at listener

**Owner:** Chat B, sole active SpawnPK-Client development chat under the [retirement handoff](V309_CHAT_A_FINAL_RETIREMENT_HANDOFF_TO_CHAT_B.md) at `9978f3f`. Issue #1117 is the coordination record; #1084 stays OPEN/DRAFT as historical source-backed evidence. Server reconstruction repositories are separate.

## Integration performed on ACTUAL private source, not public review diff

Retrieved and independently opened the *complete* private Chat A `SpawnPK_v309_R247_CHAT_A_CACHE_INTEGRATED_PRIVATE.zip` (SHA256 **`c7b4a64aa464a53b516cabe1322071ff40ab7ba20743ffad4c7d69b76ed7299f`**), the last runnable private Chat A baseline. It contained **cache R236** helper SHA256 `d63d0cc78f27af4452307646c098cd35ceac2584283f0f612b862cd18a306b72`, not the previously assumed R234. Importing the R234-only cumulative overlay would have been unsafe.

Independently opened the **newest verified cache R246** private donor `SpawnPK_v309_R246_PREPARING_WITNESS_GUARD_PRIVATE.zip` SHA256 `386159028dd9fb29f37432bca3c2c3588e43d07a6d874e5a0e6ddfa95d35d830`. Its cache helper SHA256 is `030284641b3ce50a6e9324bb2bc96c83b8a2982db0ffd8fa41330b4139615ed2`.

Applied **ONE** source-only replacement in private extracted R247 source:
`source/rs/cache/updater/assets/CacheUpdateTransaction.java` R236 → R246. Other **1,276 Chat A Java files** retained byte-identically, including distinct `rs/network/LocalEndpointPolicy.java`, real GUI, downloader, CacheUpdater, shader/graphics, login, plugins and map handling. This is **NOT** donor full-tree replacement or public source release.

Compiler: Java 21 JDK targeting Java 11 (`javac --release 11 -proc:none -g:none`), using the exact pinned compile-only lib, **1,277 production Java / 1,386 .class / ZERO errors**. The donor itself separately compiled 1,388 classes because its non-cache source differs, including the donor's `SafeDownloadTransfer.java`; do **not** infer 1,388 classes in canonical R247.

**Integrated cache regression:** 31/31 compatible Java test programs exited 0 after using original donor's 7 **documented adapted historical fixtures** (R226, R227, R234, R235, R236, R237, R238). One program explicitly states `R228_WINDOWS_ALIAS_NOT_APPLICABLE` on Linux, so **30 were meaningfully exercised on Linux, 1 compiled/not applicable**. Two donor-only download tests (`R219_DownloaderRegression`, `SafeDownloadTransferRegression`) are NOT compatible with Chat A's distinct downloader and were **excluded, not passed**. Included 65-check R246, real cache extract, ZIP traversal and separate JVM crash/locks.

## Independent actual local GUI + map-ready receipt

- Recompiled **1,277-source diagnostic-only R263 Client.java logging overlay** against the **new unified R247+R246 source**, producing 1,386 classes; production Client.java remained unchanged.
- Used real user-provided archived `.spawnpk (3)(1).zip` (SHA256 `9de2ccf52a24455a1161fd8c215c3e6e7d14fdbbf65c8084538b043c20386b7f`) staged in a separate HOME; `client.jar` SHA256 `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6` served **only non-.class assets**, including remapped GPU GLSL. Missing plugin icons had transparent diagnostic-only placeholders, explicitly **not production content**.
- Ran real reconstructed Java client under Linux Xvfb, with disposable fake credentials and localhost-only synthetic login response code 2; server parsed one-time ISAAC session seed, did not retain login bytes. Sent inbound `249` player identity (3 bytes), `73` region **chunk coords 400,400** (4 bytes), and minimum `81` player sync (2 bytes).
- Reproduced `R263_SCENE_BUILD_ENTER graphics=2`, `R263_SCENE_BUILD_EXIT graphics=2`; client live packet capture recorded **C>S opcode 121 at socket flush**, not just Java enqueue.
- In an **independent sustained server replay**, received **101 post-login bytes** SHA256 `2e56d2a9d61f6fff73c9d4105610cb6393877f00a3d03980ca483a9902561874`; using one-time outgoing ISAAC seed, the listener decoded eight source-captured packet boundaries at offsets `[0,3,21,31,32,33,34,35]` as `[185,103,103,0,0,0,0,121]`, every opcode matched. Thus **map-ready opcode 121 RECEIVED and ISAAC-DECODED at localhost listener**, advancing beyond prior R263 enqueue-only proof.
- Actual Linux screenshot captured, GUI, chat, inventory and minimap present. **Terrain still black and local player model absent**; no persistent playable world and no real online authentication. Test session later closed and client tried reconnecting. No native Windows acceptance.

## Private deliverable and hashes

**Single complete private bundle:** `SpawnPK_v309_R264_UNIFIED_R247_CACHE_R246_MAPREADY_RECEIVED_PRIVATE.zip`, **SHA256 `0b3ce907e207f8067523171c4b94682ac71f952fe4a3a26406fec18adca94651`**, 40,435,676 bytes, 1,335 ZIP entries; double-build SHA identical, ZIP CRC, source/JAR hashes checked.

- New compiled canonical class-only source-built JAR SHA256: `f328bceb0a5811426e7e10bd40ddcc9381c10af86d368dead758f00fc5fda29b`.
- Diagnostic-only compiled JAR SHA256: `ed2ae16a002936384becf910d57077362760ccf4c4e8972053bc401b10bcb962`.
- Diagnostic non-class resource overlay ZIP SHA256: `d988b51c47456d1e64f997c5eca0f9a5e63e9bff50c220223ed8506f6272ef29`.
- Bundle includes complete private canonical merged source, original-independent dependencies, 31 adapted regression programs/results, Windows rebuild/check PowerShell script, SHA-guarded one-file R236→R246 source installer/backup, source per-file checksum inventory, redacted protocol verification, real screenshot, diagnostic-only source/JAR, localhost test protocol and isolated non-class resource overlay. The 203MB authentic game asset ZIP is **not copied** into bundle; SHA pinned.

## Remaining priorities

1. **R265** source-backed initial local-player appearance and movement sync; explain why viewport is black although graphicsMode=2/map-ready 121 is received. Persistent local server should handle outgoing heartbeats and region replays rather than closing at fixed timeout.
2. Native Windows owner machine: full Java compile, exact helper/source hash, executable GUI login/world test and cache real-path cases. Linux pass is **not** a Windows pass.
3. Original-v309 source equivalence and deobf/tree release rights separately (#1004, #1114); a compiled reconstructed client is NOT a fully proven original-equivalent source tree.
4. PR hygiene: keep retired Chat A #1084 as historical draft; do not merge old stacked cache PRs into this new integration blindly. New unified Chat B branch is authoritative for coordination.

**Publication boundary:** This public branch contains documentation and non-proprietary test evidence only. The private original-derived Java source/JAR remains in the checksum-pinned private bundle until explicit source publication is authorized. Do not claim hosted full client Java CI or merges.
