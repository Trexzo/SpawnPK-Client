# Cache R243 — preserve staged data when the original disappears before backup relocation

Lane B cache-transaction work only. Coordinate with issue #1117 and Chat A's canonical integration PR #1084.

## Reproduced fault

R242 still had two early rollback states which could recursively delete `staged/` despite having **no live original cache** and **no `previous/` backup**:

1. In `PREPARING`, before writing any staged installation witness, a preexisting cache may already have been copied into `staged/`. If an unrelated process removed the live root before recovery, the surviving staged copy could be deleted automatically.
2. In `STAGED`, a V2/V3 journal can explicitly say `HAD_ORIGINAL`, yet with both live root and backup missing, R242 could still delete `staged/`. Old V1 `STAGED` journals have no reliable origin marker, so a nonempty stage is conservatively preserved.

The new regression **fails against the unmodified compiled R242** with `AssertionError: Deleted the sole staged copy: SPK-CACHE-TRANSACTION-V3 PREPARING`. R243 refuses early recovery when the original cannot be accounted for and stage may contain surviving bytes. It preserves the stage and journal, reporting IOException for manual inspection.

Normal empty `PREPARING` cleanup, genuine `NO_ORIGINAL` `STAGED` recovery and `HAD_ORIGINAL` `STAGED` rollback with a live original still present pass.

## Verified private production source

- Only modified source: `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
- Required R242 preimage SHA256: `4b4225fa6b7dd25f21a6cb330e4f6ccaa4b71a8241531c6c42059680ab33e7f2`.
- R243 postimage SHA256: `874428025bf3b6f71d66fc81ead70ef04e2322dbd3290a8666532d92dac39051`.
- Exact source diff: `tools/java/r243/R243_EXACT_SOURCE_REVIEW.diff`, 1,937 bytes, Git blob SHA1 `70bdbe0c77ec6ddb466356422d23b46cb7e22f1d`.
- Full `javac --release 11 -proc:none -g:none` compiled **1,277 actual private Java files** to **1,388 classfiles**, **zero compiler errors**.
- Compared with R242, precisely **one Java source** and **one compiled classfile** changed. Other 1,276 Java files and 1,387 classfiles are byte-identical.
- **30/30 offline regression programs passed**. The new R243 suite has **20 assertions** across V1/V3 PREPARING, V2/V3 STAGED, empty first install, witnessed first install and normal old-cache rollback. Inherited real cache extractor, HTTP downloader, ZIP-safety and cross-JVM crash/lock tests pass.
- Windows case-insensitive alias branch **compiled but was not run** on native Windows. This PR is review-only, not hosted R243 full-source CI.

## Private package and simplified Chat A integration

Complete deterministic `SpawnPK_v309_R243_EARLY_STAGE_GUARD_PRIVATE.zip` SHA256 **`ea1ee320aaeb312f8f6a0172aaf433a4942ef34d0cd0ff08e6d01eb95bf4f6f7`** (22,545,877 bytes; 65 entries).
Nested:
- `R243_CHANGED_ONLY.zip` SHA256 `041b25c99011b2373bd997dc31f98f8636661d694602f1d4c8f5ff1d331fa0cb`.
- `R243_R234_TO_R243_CUMULATIVE.zip` SHA256 `25859c296b9fcac218bdd37f650313ec8fc314f6ee174058b96a05fff322e629`.
- `R243_COMPLETE_SOURCE_PRIVATE.zip` SHA256 `3006a3f09cd8a79e425e95b3cb90f30f7aaf449a21fb44480a3324f0096463c6`.
- `R243_SOURCE_BUILT_PRIVATE.jar` SHA256 `8b5c890aaec2ac93e9843bd159a512414dd8be17f9200683326fbb1f64562ec4`.

Outer ZIP rebuilt twice identically; CRC, nested archive contents and SHA-256 hashes checked. Package holds the rebuilt private source, JAR, pinned non-game dependency JARs, one-file incremental and cumulative PowerShell patchers with `.bak`/rollback, scripts for full Windows Java11 recompilation and 30 regression programs, test sources and reports.

**Direct one-step R234→R243 option:** Independently compared **all ten complete R234–R243 donor source snapshots**; the same 1,276 other Java files were unchanged throughout. The provided `R243_Apply_R234_CumulativeOverlay.ps1` only accepts exact canonical R234 helper SHA256 `bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad` before writing the final R243 helper SHA above. If the canonical helper is already R242, use `R243_Apply_CheckedOverlay.ps1`. Otherwise **STOP, report conflict, do not overwrite**.

Retain Chat A's other 1,276 current client source files and all GUI, network, shader, cache loader and asset updates. Rebuild the actual combined canonical client and rerun Windows and GUI/localhost tests independently; a clean donor build alone cannot prove this integration.

## Known limits

This is a **conservative preservation** policy: stage bytes left by a failed first install can now require manual review rather than auto-cleanup. It does not prove the staged bytes belong to a removed original, and no physical power-loss durability, simultaneous hostile-writer race freedom, authenticated gameplay, native Windows client startup, or original obfuscated-bytecode parity is established. Keep draft; do not merge to main solely on donor evidence.
