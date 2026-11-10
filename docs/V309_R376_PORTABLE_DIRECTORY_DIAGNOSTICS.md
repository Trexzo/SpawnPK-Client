# R376 — portable directory-sync diagnostics and safe staging inventory

**Repository:** `Trexzo/SpawnPK-Client`. **Stacked on:** R375 draft PR #1170. Keep **DRAFT and UNMERGED**. No private Java source or executable is part of this public PR.

## Source-backed findings

The R375 private `LoadoutStore.java` attempts parent-directory forcing after writes and deletes. Filesystem providers differ: Java may accept the operation on Unix-like local filesystems and reject it on Windows and ZIP providers. The existing R375 catch is nonfatal, correctly avoiding false rollback, but emits the same warning after every unsupported operation. R375 also intentionally leaves aborted staging files for later inspection, because silently deleting recovery evidence is dangerous.

R376 modifies **only** `rs/gui/loadouts/io/LoadoutStore.java` in the owner-private 1,277-source reconstruction:

- Suppresses repeated directory-force warnings **once per normalized parent path per process**; it does not claim metadata durability when forcing is unsupported.
- Adds a **private, read-only staging-candidate inventory** with five narrowly defined stage prefixes. The inventory only returns sorted file names and `FILE`/`UNSAFE` metadata; it never reads contents, deletes anything, or treats stage files as a committed recovery receipt.
- Uses `NOFOLLOW_LINKS`, bounds the number of scanned entries and returned candidates, and excludes published rename/version receipts and lock files. A candidate can still belong to an active writer.
- Preserves the R374/R375 atomic moves, checksums, cooperative locks, sidecar cleanup, version receipt replay and on-disk formats. No automatic cleanup or changes to caches.

## Verification

Owner-private Linux/JDK21 source-backed scratch harness: **23/23 new assertions passed**. It exercises stage filters, symlink detection, immutability and non-deletion, invalid parent rejection, and unsupported ZIP-provider warning suppression. Inherited actual-source suites: **334 assertions passed** (including the R375 24, R374 32, R373 45, R372 56, R371 16, R370 29, order.settings 28, store 44, serializer 60).

Full private OpenJDK21 `javac --release 11` compilation: **1,277 Java sources → 1,388 class files**. Full independent fresh build-kit extraction reproduced JAR SHA-256 `5593e9da20fa51221b92ae62f0867b9be6c057eea2b3fdb3b395b4df2c67f69d`.

R375 source ZIP SHA-256: `cee56d16285f3c2592c6c9e354a4b90ba20f031570adbfcb522f070c8701450f`.
R376 source ZIP SHA-256: `030f378e4ba871ef1e7d269e1b1f655f01a82f084df92d650cf78dc7cb25c671`.
All 1,277 source hashes verified: exactly **one source** changed.

This public PR contains a static archive verifier, 26 synthetic regression tests, a private-source SHA witness, this report, a generic Java filesystem-provider probe, and a Windows/Ubuntu Python 3.11/3.13 + JDK21 workflow. Hosted CI cannot compile the proprietary reconstructed source; the standalone Java probe **does not run the game client**.

## Explicit exclusions

No real Windows private-client run, physical power interruption, parent-directory fsync durability proof, original-v309 binary parity, full atomic multi-file transaction, authenticated login/reconnect, live user cache, v312/updater compatibility, or protection against noncooperative writers. No original v309/v312 files, updater, live servers or user caches altered. **Source-M1 release gate CLOSED. DRAFT / UNMERGED.**
