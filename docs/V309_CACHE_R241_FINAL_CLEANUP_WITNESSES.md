# Cache R241 — verify both cache trees immediately before final cleanup

**Lane B, cache helper only.** Coordinated through issue #1117. This research branch provides the *exact review diff* and private-source acceptance evidence; it does not overwrite the canonical Chat A client.

## Verified remaining R240 cleanup gap

R240 verifies the promoted live cache and the original backup during the main install path, but its `finally` block verifies **only the original backup** immediately before recursively deleting the recovery workspace. If a non-cooperating writer changes the promoted cache between those two steps, the main code can still return success and discard the previous known-good copy.

R241 adds a package-private **deterministic pre-cleanup fault-injection hook** without changing public callers. For a completed V3 installation it then requires a still-valid V3 `PROMOTED` journal, nonmissing install witness, matching **live promoted cache** fingerprint and matching **original backup** fingerprint (if one existed) immediately before deleting the workspace. A failed final check propagates IOException to the original install caller and leaves the live data, previous backup and journal for recovery. Inherited error-path rollback behavior remains unchanged.

This closes the demonstrated *verification gap*; it does not establish a race-free atomic deletion or prevent an outside writer after the final hashes.

## Independent private build and regression evidence

- **Only changed production source:** `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
- Exact R240 source preimage SHA256: `d70ac2ba3c1931ba01f5e77c75e0d3fedaf43b3baff21269c462df4c4a3bd3b5`.
- R241 source postimage SHA256: `e1071509d9ac3044cb939ee9504ee057214a5e5ccb8cfff8457ea6c4d29fa3fc`.
- Public exact source review diff: `tools/java/r241/R241_EXACT_SOURCE_REVIEW.diff`, 4,906 bytes, Git blob SHA1 `5703744b6558d9ce512ec1d61cfcb15cc4a11931`. Independently verified byte-identical to the private source comparison.
- Full private `javac --release 11` on **1,277 real Java source files** produced **1,388 production classfiles, zero compilation errors**. Exactly one production classfile, `CacheUpdateTransaction.class`, changed versus R240. The remaining 1,276 sources and 1,387 classfiles match.
- **28/28 offline Java regression programs passed.** New R241 deterministic final-cleanup test **34 checks** (live same-size/mtime tampering, original-backup tampering, missing witness, foreign workspace files, first install, normal completion and recovery replay). Includes inherited downloader, authentic cache extractor, ZIP traversal, cross-process crash and lock tests.
- The R238 inherited regression fixture was adapted **TEST-ONLY** because R241 now reports blocked final cleanup as IOException rather than silent install success. Six earlier test-only compatibility fixture changes were retained. No other production Java changed.
- The initial regression attempt encountered a **test-system inode exhaustion** after 27 passes. The test runner now isolates and removes temporary fixtures for each program; the clean full rerun passed 28/28. Do not count the first run as full acceptance.
- Windows scripts are packaged but **were not executed on a native Windows game machine**. No hosted R241 Java CI is claimed by the review-only PR.

## Verified deterministic private handoff

- Complete private bundle: `SpawnPK_v309_R241_FINAL_CLEANUP_PROVENANCE_PRIVATE.zip` SHA256 **`16076c488431dfa83ff0e93266362faf2e234b82d02d2e92dd06587f94ae5261`**, 22,543,415 bytes.
- Internal changed-only `R241_CHANGED_ONLY.zip` SHA256 `c08f50dbf82817cbd10f81f3e5bf06330e02a87400b30ba6fbce27c4125d0297`.
- Private complete source ZIP SHA256 `76b456ab29fd1e3484879aded09018aa6d605c6c553945188fe39682d1c3fbb8`.
- Java11-target compiled class-only JAR SHA256 `81ffbd321e51f28eec61296ddc4e2cdb5a13b4b2d8341bd42be2e352cd426f7c`.
- The outer ZIP was built twice with an identical SHA256; ZIP CRC, source count, class count and nested SHA256 checks all passed. Includes in-ZIP checksum-guarded PowerShell **one-file overlay**, R240 source backup, rollback path, dependencies, full Java source and JAR, Windows Java11 rebuild and 28 regression fixtures/logs.

## Lane A integration contract

Last confirmed canonical Chat A title is R242 with cache R234; newer world-protocol research in the same PR does not itself prove cache R241 integration. Read the **actual helper SHA** first. If still R234, apply cache **R235 → R236 → R237 → R238 → R239 → R240 → R241** sequentially, verifying each source preimage and rebuilding the **canonical** 1,277-file client at each stage. **Only** overwrite `CacheUpdateTransaction.java`; never replace Chat A's CacheUpdater, downloader, Java GUI, asset recovery, launcher or networking with the donor source tree.

Native Windows private game testing, authenticated gameplay, real hardware power cut, malicious witness/journal alteration and arbitrary outside post-hash writes remain unresolved. **Keep draft; no merge to main.**

## Verified one-step R234 → R241 canonical integration option

Chat A's PR #1084 currently titles its most recent accepted **cache helper R234** even though its protocol/world testing has progressed beyond R254. To avoid burdening Chat A with seven separate helper-only merges, the private full ZIP now also includes **`R241_R234_TO_R241_CUMULATIVE.zip`** and **`R241_Apply_R234_CumulativeOverlay.ps1`**.

I independently hashed **all 1,277 Java sources in each of eight actual complete donor snapshots R234, R235, R236, R237, R238, R239, R240, R241**: the exact same **1,276 other Java source files** persist throughout. The helper preimage `bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad` can therefore be replaced **directly** with final R241 postimage `e1071509d9ac3044cb939ee9504ee057214a5e5ccb8cfff8457ea6c4d29fa3fc`, changing only the one helper source. The cumulative script refuses any unknown source hash, creates a verified timestamped backup, checks the replacement digest, and rolls back on error. It never overwrites Chat A's 1,276 other sources, GUI, downloader, cache extractor or launcher.

- Cumulative nested overlay ZIP SHA256: `dff961dc5e819850d3d83142e2c8962f6f0a0a54b360683b2bad88c525b7f450`.
- Earlier incremental R240→R241 changed-only ZIP SHA256 is unchanged: `c08f50dbf82817cbd10f81f3e5bf06330e02a87400b30ba6fbce27c4125d0297`.
- Full private combined bundle SHA256 after adding this option: **`16076c488431dfa83ff0e93266362faf2e234b82d02d2e92dd06587f94ae5261`**.
- Both package builds deterministic, ZIP CRC and nested source/compiled JAR/dependency checks pass.
- **IMPORTANT**: Direct overlay is valid only when the actual Chat A `CacheUpdateTransaction.java` SHA is exactly the R234 preimage. If it has changed, refuse/stop and reconcile. After applying, Chat A must independently recompile the complete canonical 1,277-source tree, run merged cache regressions, and replay its own GUI and localhost login tests. Private donor compilation does not prove merged R254 runtime acceptance.

