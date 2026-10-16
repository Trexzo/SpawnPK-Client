# Cache R225 — detect stale staged-cache snapshots

Ownership Lane B, coordination #1117. **Distinct from original bytecode/deobfuscation R225 and Lane A runtime R231.**

The exact compiled private source in `src/rs/cache/updater/assets/CacheUpdateTransaction.java` is mirrored by `tools/java/r225/CacheUpdateTransaction.java` (Git blob SHA1 `a331c056e11a9cdebd1785733d9a58bbc252ef03`; exact local private Git blob verified).

## Changes to production source

- Hashes the active cache's regular-file contents using SHA-256 and includes relative directory/file names.
- Verifies that its staged copy matches the initial live snapshot before extracting.
- Verifies the live cache again just before swapping directories; preserves any external writes, even same-size and timestamp-restored edits, plus file creation/removal.
- Refuses to replace a previously absent root if another writer created it during extraction.
- Rejects symlinks/device-like entries introduced into the staged output by a custom extractor.
- Checks available disk space against original cache byte count **before** an expensive staged copy; this is an early refusal, not disk-space reservation or a disk-full guarantee.

## Actual PRIVATE acceptance

- Exact private R224 input bundle SHA-256 `70e3afb20cd235813918ea11e1f9789e47699a98d2055f17d1e895f3c3e4ed02`.
- ONE production Java source differs from R224; preimage SHA256 `690417259a7343a7a5f1134a1b0b05693acef7b207c8d6998d0b6182a94b3409`; postimage SHA256 `9be38338d50c7a774d070e00ad6c426dc363180ef2c8d83c052b6baa41b78e43`.
- Full `javac --release 11` of **1,277 Java sources, 1,388 classfiles, zero compilation errors** (with deprecation/unchecked informational compiler notes).
- **12 offline regression suites pass**, including the new 22-assertion mutation/space/unsafe-stage regression, cross-process crash recovery, real CacheUpdater archive integration and staged download.
- Versus R224 class JAR: only CacheUpdateTransaction.class and nested same-owner classfiles change; two new nested classfiles appear. No other game Java changed.
- SHA256 complete private bundle `9a9fa2c760c1a195b34314acef01600351cc2fda645ad0ac232a4288a6166674`.
- SHA256 changed-only ZIP inside `dbc0012ab5a30e2f1ad4af688e97a0bb5f4b2b830a26048b57681900822d65c9`.
- SHA256 source ZIP `836b32a7392d7bade70e0ad0facdb2b3144c561583b9280ce28770d1faea54e4`, production JAR `00b876ef37fc2bce03ea5b0b257799400483fc1bb45943985fa6b758ece09b5a`.

## Handoff and limits

Lane A is at integrated R231 with our R224 rollback fix. It should preflight R224 transaction SHA, overlay ONLY `CacheUpdateTransaction.java` from the changed-only ZIP, keep merged `CacheUpdater.java`, `AssetUpdater.java`, `FileDownloader.java` and full GUI sources untouched, then run its integrated full build and resource-backed graphical startup.

The **full private client has not been compiled or tested on native Windows**, and the independent public GitHub helper smoke currently has **no accepted hosted CI execution** for R225. Existing R220-R224 public CI cannot verify the new R225 helper. No power-loss durability claim; no strict protection against writes in the gap after the final fingerprint comparison. Content hashing adds substantial disk I/O; no actual large-asset performance benchmark was run. This branch must remain DRAFT.
