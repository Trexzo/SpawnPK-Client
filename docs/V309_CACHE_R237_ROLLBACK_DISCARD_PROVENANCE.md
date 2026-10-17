# Cache R237 — verify every cache directory before destructive rollback cleanup

**Ownership:** Chat B, `CacheUpdateTransaction.java` only. Review-only branch stacked on cache R236 and coordinated in #1117. The private source tree is a donor snapshot, not the canonical Lane A runtime.

## Verified data-loss window

During `PROMOTING` or `ROLLBACK_PREPARED` recovery with an old backup, R236 could move the active directory to `interrupted-new/` and erase it when cleaning up the workspace **without verifying those files were the originally staged installation**. A non-cooperating writer could create/alter the live cache or edit the quarantine, and recovery would delete its unrelated data.

R237 compares the disposable active and quarantined trees with the persisted installation fingerprint before moving or deleting them. It rehashes after the quarantine rename and again before deleting the recovery workspace. The additional checks cover `ROLLBACK_PREPARED` replay with and without `previous/`, `ROLLBACK_RESTORED` cleanup and ordinary rollback after `PROMOTING`. On mismatch recovery fails closed, retaining active/quarantined data, previous backup if still present, and transaction evidence. Genuine historical V1 witnessless journals preserve their legacy behavior.

## Actual source and classfile evidence

- **Only production source changed:** `src/rs/cache/updater/assets/CacheUpdateTransaction.java`
- R236 required SHA256 preimage: `d63d0cc78f27af4452307646c098cd35ceac2584283f0f612b862cd18a306b72`
- R237 SHA256 postimage: `4fb08b5755ea27aa87b3c7afe983383b480a0da143d42567d5f5a2e4f4838f9a`
- Exact reviewed diff Git blob SHA1 `3dab58d2663ce8dfe37b4d311fadb50aa717d6fe` (4,529 bytes), independently matched to private source comparison.
- All 1,277 actual private Java sources compiled using `javac --release 11 -proc:none -g:none` with an available JDK21 compiler: 1,388 production classfiles, zero errors.
- Exactly one source and one compiled classfile differs from R236. The other 1,276 Java files and 1,387 classfiles match.
- **24/24 offline regression programs pass.** R237 new regression **54 checks pass**, including same-size/mtime mutation, foreign live-root creation, tampered live root during prepared rollback, edited quarantine with backup still present, tampered quarantine after original restoration, valid replays, and historical V1 compatibility.
- Included Windows source rebuild and all-24-suite regression scripts are prepared but **not executed on native Windows**. Hosted R237 Java CI is **not** available because the public branch includes the review diff, not the full source helper.

## Verified private donor

- Bundle `SpawnPK_v309_R237_DISCARDED_CACHE_GUARD_PRIVATE.zip` SHA256 **`695fb188b6ed74da586327f3fd492f6b2a7e64f9d60893f8f0d6ac33e3601068`**
- Internal changed-only ZIP `R237_CHANGED_ONLY.zip` SHA256 `b19ac1bf4fb54a92be0ab5343bf3c39aab375a798f403b4b52a797c0f0d68cc3`
- Full source ZIP SHA256 `aafa84b0fb7050f4e57a46140c4f28b607002e9decf862831f1476fccae88c8d`
- Compiled class-only JAR SHA256 `47acebd29aa246af5fc3066cec5228364ef9d82f50b24901d3792513998284b8`
- Archive rebuilt twice with identical hash; ZIP CRC and nested source/JAR/dependency hashes verified. Includes preimage `.bak` and direct-from-nested-ZIP SHA-guard PowerShell installer, source, compiled JAR, non-game dependencies, 24 regression programs/logs, and Windows build scripts.

**Chat A integration:** canonical PR #1084 last confirmed R242 with cache R234. Apply private **R235 → R236 → R237 sequentially** after each exact SHA-256 preimage check, replacing only `CacheUpdateTransaction.java`; retain all canonical Lane A GUI, cache extractor, downloader, networking, login and launcher changes. Recompile actual integrated Java11 source and repeat cached helper tests, GUI render and localhost login smoke. If any preimage differs, stop and report conflict in #1117.

**Not proven:** private Windows gameplay and authentication, physical power-loss durability, immunity from hostile writers after final hashing, bytecode parity with obfuscated original or security against tampering with both journal and witness. **Keep draft; no merge.**
