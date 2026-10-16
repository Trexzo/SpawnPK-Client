# R224: repeatable rollback after interrupted cleanup

Lane B cache-only security/reliability patch, coordinated in issue #1117; parent R223 #1119. Only one real private production Java file is modified: `src/rs/cache/updater/assets/CacheUpdateTransaction.java`. The independent public version is `tools/java/r224/CacheUpdateTransaction.java`.

## Verified defect and repair

Previously the original cache could be moved back from `previous/` to the live root while its on-disk marker still said `PROMOTING`. If cleanup failed or the JVM stopped before cleanup, repeated recovery could interpret the restored original as an uncommitted new cache and delete it.

R224 journals rollback as `ROLLBACK_PREPARED`, then `ROLLBACK_RESTORED`; a separate `ROLLBACK_EMPTY` phase covers installations with no previous root. Recovery of each incomplete phase is repeatable, preserving the original cache. Conflicting states fail closed.

## Private build and tests

- Original R223 private source SHA256: `feec444dbd6e4857451626e675d162b1e8756c10401741bb891332ab22440de5`.
- New R224 production helper SHA256: `690417259a7343a7a5f1134a1b0b05693acef7b207c8d6998d0b6182a94b3409`.
- Full Java11 source build: **1277 Java files, 1386 classfiles, 0 errors**; only CacheUpdateTransaction.java and its .class differ from R223.
- New private rollback-replay suite **21 checks passed**, including interrupted cleanup/restart and injected IOException during download/extraction.
- **All 10 inherited private regression suites passed**, including separate JVM lock/halt, real CacheUpdater extractor, downloader and ZIP safety.
- ENOSPC is simulated by IOException; native disk-full and power-cut durability are NOT proven.

## Private SHA-pinned handoff

- Complete private R224 ZIP SHA256: `70e3afb20cd235813918ea11e1f9789e47699a98d2055f17d1e895f3c3e4ed02`.
- Source ZIP SHA256: `aa68eca0211afb2ac3997914fd3d06470bfe4af9405040083040c97656fcf586`.
- Changed-only overlay ZIP SHA256: `332a1537220834beeb23191b0a38ca271c6c4f896a8d851fa8c55ef8b3bb2446`.
- Java11 class-only JAR SHA256: `f977cff2aaecab0ad52bff5ca38af9a86bfec9925c1a7929bb0f03f4a1523114`.

Lane A must overlay ONLY this changed class after preimage SHA check against R221/R222/R223, preserving its integrated CacheUpdater, FileDownloader, launcher and GUI. Rebuild Lane A's current source and run integrated tests. Public GitHub Java11 tests are synthetic; private Windows game runtime and actual gameplay remain unverified. Do not merge on synthetic tests alone.