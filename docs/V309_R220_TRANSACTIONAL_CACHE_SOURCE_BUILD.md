# R220 — transactional v309 cache replacement (private source build)

**Track:** staged cache safety on the separate readable-source R219 lineage. This is NOT the independently progressing R220/R221 original-bytecode/parity research.

## Actual production changes

- Replaced the pre-download recursive deletion in the PRIVATE real `rs/cache/updater/assets/CacheUpdater.java` with a call to newly written source-independent `CacheUpdateTransaction.install`.
- The new helper exists publicly as `tools/java/r220/CacheUpdateTransaction.java`; its exact Java source is also included in the private client tree at `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
- Stages a copy of the current cache on the same filesystem; rejects existing symlinks/unusual file types rather than following them; downloads ZIP outside the active root; extracts to the staged copy; replaces the root only after extraction passes.
- An interrupted download, rejected ZIP, or failed extraction leaves the active root alone. If the first directory rename succeeds but the subsequent promotion fails, rollback restores the original directory; if rollback itself fails, the backup is retained for manual recovery.
- Cache archive entries under independently versioned `sprites/`, `configs/`, and `versions.dat` are ignored, with skipped file data still counting against ZIP expansion limits. The manager remains responsible for writing the new cache version after successful download.

## Exact local private verification

- Base R219 full-source ZIP SHA-256: `51591af8b04071d4cea520da9cd0575963e80e75a3bb3d194eb8b0d431b5241b`.
- Actual changed preexisting private Java source: **one** (`CacheUpdater.java`); actual newly added Java source: **one** (`CacheUpdateTransaction.java`). All 1,275 other R219 Java source files match byte-for-byte.
- **1,277 Java source files**, `javac --release 11` using JDK 21, **0 errors**, producing **1,385 classfiles**.
- Synthetic private transaction regression: 8 cases passed (null and rejected downloads, download exceptions, failed/exceptional extract, forced failure after first rename and recovery, invalid download destination, success and preserved assets; plus existing-cache symlink rejection where supported).
- REAL private `CacheUpdater.extractCache` integration: malicious ZIP rollback and successful ZIP promoted, protected sprite/config/version records unchanged.
- All 5 existing R219/R218 regressions passed (downloader, transfer, ZIP-path, bounded extraction, offline updater).
- Complete private bundle SHA-256: `752a2eb4a5ff448a594d4f8d715492479d8dbd31935ffc32813846095e4a5f43`.
- Source-built JAR SHA-256: `97fe7136e82939537ada9da5d9c3ca4e4c0a58aeb47c4bcfb1c18feb702e45db`.

## Strict limits

The public GitHub Java 11 Ubuntu/Windows workflow exercises only the standalone new helper with synthetic input; it does **not** contain the original-decompiled private game source, exact private runtime dependencies or real-game cache files. Full private Windows replay, live-file/second-instance behavior, crash between the two renames, complete original-bytecode parity, graphics/gameplay and distribution remain **unverified**. Copying a full cache to staging consumes extra disk space; conservative overlay retains old unknown cache files. Directory replacement is rollback-capable but not a one-step whole-root atomic transaction. Do not merge solely on synthetic CI.

## Private handoff

`SpawnPK_v309_R220_CACHE_TRANSACTION_PRIVATE.zip` contains the complete SHA-pinned source, compiled JAR, external non-game libs, a changed-only ZIP with the prior `CacheUpdater.java.bak`, Java regressions, and `R220_Rebuild_Verify.ps1`/`R220_Windows_Regression.ps1`. Use only isolated rebuild/test scripts; no production game endpoints are needed.