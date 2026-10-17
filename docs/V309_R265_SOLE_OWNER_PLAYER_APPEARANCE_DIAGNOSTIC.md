# R265 — sole-owner R247+R246 rebuild and local-player appearance framing

This is a continuation of unified [R264 PR #1141](https://github.com/Trexzo/SpawnPK-Client/pull/1141) after Chat A retirement commit 9978f3f. **Only Chat B owns active SpawnPK-Client work now.** PR #1084 is historical, retained as a draft.

## Revalidated integrated source

The actual private `SpawnPK_v309_R247_CHAT_A_CACHE_INTEGRATED_PRIVATE.zip` was retrieved. Its cache helper preimage SHA256 was **d63d0cc78f27af4452307646c098cd35ceac2584283f0f612b862cd18a306b72**, confirming **R236**. Replaced **only** `rs/cache/updater/assets/CacheUpdateTransaction.java` with exact R246 helper SHA256 **030284641b3ce50a6e9324bb2bc96c83b8a2982db0ffd8fa41330b4139615ed2**. All other **1,276** R247 source Java files were retained without edits.

An independent `javac --release 11 -proc:none -g:none -encoding UTF-8` compiled **1,277 private Java sources to 1,386 classfiles**, zero compiler errors. A separately instrumented, diagnostic-only Client.java version also compiled independently to **1,386 classfiles**; **not** part of canonical production release.

Selected integrated Java regressions independently executed against these actual new classes:
- R242 missing original backup: **22 checks passed**.
- R244 PREPARING stage ownership: **30 checks passed**.
- R245 MOVING_OLD original witness: **40 checks passed**.
- R246 persisted PREPARING witness: **65 checks passed**.
- New source-backed appearance mask Packet regression: **10 checks passed**.

A fresh 31-suite sequential runner was **not completed**: it reached its execution timeout after multiple successful programs, so **DO NOT claim a new 31/31 run here**. Prior R264 evidence documented 31 compatible suites in an independent run.

## Source-backed reason local player is absent

`Client.finishLogin()` creates `localPlayer = players[2047] = new Player()`, but does not initialize appearance. `rs.model.Player.method279()` returns null when `!hasAppearance` (unless separate force-hidden-model special handling). Player appearance decode `Player.method3589(Packet)` sets `hasAppearance=true`.

The inbound opcode **81** player-sync decoder calls `updateLocalPlayerMovement()`, `method1885()`, `processPlayerInfo()`, then `processPlayerSynchronizationMasks()`. A local movement update **bit 1** with type **0** marks local player index 2047 for synchronization. An update mask **0x10** calls `method2409()`, reads a **negated unsigned-byte length** via `Packet.method3095()`, copies that appearance block and calls `player.method3589()`. **The previously used two-byte `00 00` minimal opcode-81 payload does not contain this mask or any appearance block.**

The new standalone Java test exercises the **real rebuilt Packet bit-reader** with an isolated 7-byte *boundary-only* frame: `80 1F FC 10 FE 11 22`. It confirms the self update/type 0, zero retained peers, index 2047 sentinel, 0x10 mask, byte alignment, and length transformation. **The final two opaque bytes are deliberately NOT a valid appearance payload** and must not be used as a gameplay fixture. A valid body must be reconstructed from `Player.method3589` with supported equipment, animation and name values, then tested on sustained localhost world replay.

## Verified private package

`SpawnPK_v309_R265_UNIFIED_CACHE_R246_PLAYER_APPEARANCE_DIAGNOSTIC_PRIVATE.zip`

SHA256 **67273073b7e718a9eab5db44d19c6e8facf820c160a73053bcc6247418be22f3**; 25,127,406 bytes, 1,289 ZIP entries. Two deterministic builds yielded identical bytes, ZIP CRC passed.

Inside: complete unified 1,277-source production tree, Java11 rebuilt JAR SHA256 **dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503**; separate diagnostic-only rebuilt JAR SHA256 **ece94b2f5a49e8d2a07dcbe97c0456caa9618f801c77ae929a1a99a7e5b2a59a**, standalone test, source manifest, compile logs and evidence. Diagnostic `Client.java` SHA256 **01e0acd8fa79617cd31e84d39260d073aae3be18909041cef88227d7d1760870**; canonical `Client.java` SHA256 **13a7c5a386112c9ca122fd8557dfca0a77e024de8e29a203d205528b1e88fc9d**. Diagnostic logs are inserted before and after self player mask handling and after overall 81 parsing, not production changes.

## Runtime state and remaining acceptance

**Previous R264 verification** proved graphicsMode=2 scene builder and source-built localhost server **receipt and ISAAC decode of outgoing map-ready opcode 121**. This R265 batch performed *compilation and protocol regression*, **not a new interactive GUI/terrain replay**. Black terrain, local player model, appearance-body validity, sustained world/session, native Windows gameplay and power-loss durability remain **NOT VERIFIED**.

Next implementation batch: create a source-valid appearance body from the actual player decoder (no fabricated item IDs), replay initial `81` with **0x10** on a persistent localhost listener, log `R265_SELF_MASK_BEFORE/AFTER` and local model readiness, inspect screenshot and actual terrain buffers; fix the first real failing stage. Keep the prior R264 packet 249→73 (chunk 400,400)→81 and ISAAC seed behavior unchanged.

The branch contains only independently authored test/documentation. Do not publish private original-derived source or merge historical stacked PRs solely on this evidence. **Keep draft.**
