# Cache R242 — preserve staged and committed recovery evidence if original backup disappears

**Ownership:** Chat B, v309 `CacheUpdateTransaction.java` only. Coordinate in [issue #1117](https://github.com/Trexzo/SpawnPK-Client/issues/1117); Chat A owns canonical full-client integration in PR #1084.

## Actual R241 failure and R242 behavior

An interrupted witnessed install whose `.install-witness` says `HAD_ORIGINAL` should have the original cache preserved as `previous/` until rollback or completed cleanup. In R241, if this backup disappears **while the journal is PROMOTING**, the no-root + staged-data recovery branch could recursively delete the remaining stage and journal, losing all evidence. If the root is present and the journal is `PROMOTED`, the original-backup disappearance could be silently accepted and the journal discarded.

A real Java regression **fails against the compiled R241 helper** with `Recovery accepted missing backed-up original: SPK-CACHE-TRANSACTION-V3 PROMOTING`. R242 checks V2/V3 `PROMOTING` and `PROMOTED` journals with no `previous/`: when the persisted install witness says `HAD_ORIGINAL`, recovery raises IOException **before any destructive cleanup**. Stage, live cache and journal remain for manual inspection. `NO_ORIGINAL` genuine initial installs still recover normally, as do historical V1 PROMOTED journals.

**Important conservative consequence:** an interrupted prior cleanup may have legitimately removed `previous/` while leaving the journal; R242 intentionally preserves the ambiguous remaining data and requires manual inspection instead of assuming the backup was safely released. This is a fail-closed recovery policy, **not** proof that an external writer actually deleted a backup or that hardware power-loss guarantees exist.

## Exact build and regression verification

- Only changed production source: `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
- **R241 preimage SHA256:** `e1071509d9ac3044cb939ee9504ee057214a5e5ccb8cfff8457ea6c4d29fa3fc`.
- **R242 postimage SHA256:** `4b4225fa6b7dd25f21a6cb330e4f6ccaa4b71a8241531c6c42059680ab33e7f2`.
- Exact source review diff **1,581 bytes**, Git blob SHA1 `2bd2c2557d589eaffeeb5181c08d88002b5cb759`, byte-verified against the private source comparison.
- Complete `javac --release 11 -proc:none -g:none`: **1,277 actual donor Java sources, 1,388 production classfiles, zero errors**.
- **29/29 offline Java regression programs PASS**, including new `R242_MISSING_ORIGINAL_BACKUP_FAILCLOSED_PASS checks=22`. Includes 28 inherited cache/ZIP/downloader/multi-JVM lock/crash suites; Windows-only case-alias behavior was compiled but not tested on native Windows.
- Only **one Java source** and **one production classfile** differ from R241, all 1,276 other source files and 1,387 other classfiles identical.
- New fixture simulates both V2 and V3 witnessed PROMOTING (stage survives) and PROMOTED (live remains), genuine V3 first installs without backups, and historical V1. This synthetic journal setup tests the source code behavior; it is not a physical power-cut test.

## Private package and one-step overlay for Lane A

- Complete private package `SpawnPK_v309_R242_MISSING_ORIGINAL_BACKUP_PRIVATE.zip` SHA256 **`aa4cf114d9bc79f1fb2b8df5f9ea547878fe351b3d8f8c4fadeea6b32ac3fa77`** (22,542,351 bytes).
- Internal incremental `R242_CHANGED_ONLY.zip` SHA256 `ceb9753710273dbaa7534eca460b77a6b3810253bf7a025fde675f1a07ac3121`.
- **Cumulative R234→R242 one-file ZIP** SHA256 `aef024d3a28b99d4851f2aa082e2d9b74e93966d75961ee09c374a7ad97c7b51`, guarded preimage R234 `bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad`, final postimage the R242 SHA above.
- Complete private source ZIP SHA256 `e5be25acad37956832301e36ff7ccfd4ca24ec4496b7713386d411fa0872bb30`; compiled Java11 class-only JAR SHA256 `f29d3f64e82eaa3e0c224a923b93be4298824e7a5f9424b6400ac14262656983`.
- Full bundle built **twice byte-for-byte deterministic**, ZIP CRC and all inner hashes verified, exactly 64 package entries.
- Contains `R242_Apply_CheckedOverlay.ps1` (incremental R241→R242), `R242_Apply_R234_CumulativeOverlay.ps1` (R234→R242), their source backups, full source and compiled JAR, pinned compile libs, Windows source rebuild and 29-suite regression scripts, original + seven adapted test-only fixtures and JSON/log evidence.
- Independently compared entire nine-source-donor chain **R234 through R242**: exactly the same 1,276 other Java files throughout. Thus Lane A may apply the final R242 helper **directly** onto exact R234 preimage rather than overlaying eight separate revisions.

**Lane A must verify its actual current `CacheUpdateTransaction.java` hash before acting**, retain its canonical GUI, downloader, cache extractor, shaders, asset loader, login and world-protocol work, replace **only one helper file**, rebuild its own current full-client Java source and run its own Windows/live-client checks. Refuse unknown preimage; never overwrite Chat A's source tree with this donor snapshot.

## Acceptance limitations

GitHub contains **only review diff and documentation**, not a hosted Java run of the private R242 helper or proprietary full decompiled source. No native Windows gameplay, successful authenticated online gameplay, true filesystem power-loss durability, or race-free protection against unrelated writers after final verification is claimed. Keep draft and do not merge into main solely on this evidence.
