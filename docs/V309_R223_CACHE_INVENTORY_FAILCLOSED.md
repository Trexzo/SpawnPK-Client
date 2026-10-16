# R223 — Fail-closed recovery inventory for v309 cache transaction

**Ownership:** Lane B / cache-only. Coordination: [issue #1117](https://github.com/Trexzo/SpawnPK-Client/issues/1117). **Not** the R223 original-bytecode research series.

## One actual private production-source edit

The R222 private v309 `rs/cache/updater/assets/CacheUpdateTransaction.java` (SHA-256 `726262c28ca7d5f1bc1b466b805dbfdb45ef541cbdf479de1e3dd9e5e52968e6`) was updated to SHA-256 `feec444dbd6e4857451626e675d162b1e8756c10401741bb891332ab22440de5`:

1. Inventory all journal workspaces declaring the requested cache root **before** mutating the active root, its backup, or staged files.
2. Fail closed and retain every backup if two journals claim ownership. Directory listing order no longer decides which old data is kept.
3. Reject a scoped workspace whose marker claims a different cache root, without touching other roots' scoped workspaces.
4. For own root, preserve and reject unmarked staged data rather than silently ignoring it. Truly empty pre-journal orphans remain untouched.
5. Original valid R221 and R222 single-transaction recovery remains supported.

No other preexisting client Java source changed. `CacheUpdater.java` remains SHA-256 `a7276eee8c1e179de9cef9c1a13b77050435057d13c9f87c0caac9a97360a396`. No Lane-A-owned downloader/GUI/network files edited.

## Verifiable private-source acceptance

- **1,277 Java files** compile together, Java21 `javac --release 11`, **zero errors**, yielding **1,386 production classfiles**.
- Exact classfile content set versus R222 differs in only `rs/cache/updater/assets/CacheUpdateTransaction.class`; every other **1,385 .class** contents are unchanged.
- New **R223 real private-source regression: 14 assertions passed** for ambiguous duplicate journal/backup, unchanged active files on rejection, install preflight, unrelated root recovery, mismatched journal owner, unmarked staged data preservation, and restoration after manual ambiguity resolution.
- Inherited **R222 root-isolation 8/8**, **R221 hard-crash and inter-process locking 10/10**, **R220 transaction 8/8**, and real cache ZIP extraction, downloader, transfer, path traversal, staged archive and offline update checks passed.
- No actual private Windows client GUI or game session, power-cut durability, independent original-v309 JVM instruction parity, or real multi-client gameplay verification claimed.

## SHA-pinned private artifacts

- Base R222 bundle SHA-256: `56a98dff3ff2bbe37b0c7e7c8cc1e2685b688d12983c1b96feeed5d7a718a488`.
- Full R223 bundle SHA-256: `467138310f38de15f66977c7eaf9b28e35d63e214006b5dc70aeb8d2a63a0678`.
- R223 changed-only overlay ZIP SHA-256: `104056c683ca5c65323e03e8fcf451e1c05f8c617bad30877717ad4ec79e7abd`.
- Full R223 source ZIP SHA-256: `7cddfd68d790d9dde553851e48d257ad3d222e0c8fd35f2a406c8a77736b65e0`.
- R223 source-built JAR SHA-256: `a32bd4552b0e78cc9555c6cfabd0bfca746a042dcdf61488f26a563c8e119dac`.
- R221 transaction preimage SHA-256 for Lane A overlay: `73ce277d2e3371ffa84237f1f55029be0475b8a8b10b35859f36b7fd25a69861`.

The private bundle contains the complete source/JAR, precise changed-only ZIP with both R221 and R222 backups, robust SHA-pinned source-only PowerShell overlay/rollback path and Linux/Windows rebuild and regression scripts. **No proprietary Java or resource bytes committed to GitHub.** Public cross-platform workflow exercises the exact new original-independent production helper with synthetic files; it is not the private full-client Windows test.

## Integration for Lane A

Lane A's canonical current R227 source includes earlier R221 transaction recovery. Preflight `CacheUpdateTransaction.java` against the authorized R221/R222 input hashes; overlay only that one changed file. Leave Lane A's merged `CacheUpdater.java`, `FileDownloader.java`, network and GUI classes unchanged. Recompile the full integrated tree, run crash/transaction/download/asset checks and record a new unified source SHA. Any differing preimage is a conflict; stop instead of overwriting. Report integration to #1117.

**Keep DRAFT** until verified integrated Windows runtime and independent acceptance.