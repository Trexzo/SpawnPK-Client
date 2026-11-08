# R368 — v309 loadout save locking and GUI failure feedback (private candidate)

**Correct repository:** `Trexzo/SpawnPK-Client`. **Base:** R367 draft PR #1160, head SHA `3f5766cadcaaee260ff4e792b1ac1668b515678a`. Keep the complete 1,277 recovered Java sources and binary dependencies in the private owner download; this public PR contains only static verification tooling, a 2-owner SHA witness, synthetic tests, CI and this document. **DRAFT / UNMERGED.**

## Reproduced limitation in R367

R367 compares a SHA-256 fingerprint before and after staging, but has no cooperative cross-process lock. A competing writer can write between the last fingerprint and rename. Save refusal was logged to stderr and not surfaced in `LoadoutsPanel`. Adding a non-modal user-visible failure line prevents errors from being silently hidden from the graphical user. This pass **does not** prove crash durability or complete defense against uncooperative writers.

## Private R368 candidate (two source files only)

- `rs/gui/loadouts/io/LoadoutStore.java`: use a stable SHA-256-derived `.loadout_lock-*.lck` filename and acquire `FileChannel.tryLock` before validation, staging, the existing two raw-byte fingerprint comparisons, and atomic replacement. An unavailable/overlapping lock refuses the write without modifying the target. Lock files deliberately remain in place; removing a lock file while still held can break coordination by replacing its file identity. The lock file includes an **underscore** to keep it out of both legacy folder-list discovery branches.
- `rs/gui/loadouts/LoadoutsPanel.java`: non-modal `JLabel` status below the loadout control rows. The store sends failure reasons through `reportLoadoutSaveFailure`, which schedules updates on the Swing Event Dispatch Thread. No modal dialogs or automatic retries.
- Existing version-5 serialization bytes and the existing atomic replacement + fingerprint logic remain unchanged. No existing production cache or original game JAR was modified.

### Verified offline evidence

- From the pinned private R367 ZIP SHA `afd2f68dd309934725623b7a4fa05ceb0bf971b3f317dc3904bdb0442ba8cf67`, **exactly 2/1,277 Java files changed**. The new private source archive SHA and both owner SHA pairs are in `research/v309-source-recovery/r368-lock-gui-witness.json`.
- **44 source-backed `LoadoutStore` assertions** passed, including healthy saves, invalid/truncated file preservation, same-length optimistic conflict detection, same-JVM lock contention, separate JVM file-lock contention, refusal callback captured by a panel test stub, independent folder save, and ensuring persistent lockfiles are not listed as folders.
- Inherited **60 source-backed `LoadoutSerializer` assertions** passed across UTF-8 and ISO-8859-1.
- Full private Java 11-target compilation under JDK21: **1,277 Java files → 1,386 class files**. Initial and independent builds, plus the full build-kit fresh-extraction replay, produced the identical JAR SHA-256 `e6a174121b178230d444b530edbcf978e1da9649448596e9a2e87f285e8a674b`.
- **19 local public synthetic Python verifier tests** passed, plus successful static archive verification against both SHA-pinned private source archives. Hosted GitHub Actions checks are separate from these local results.

### Important remaining limitations

The lock is **cooperative**; R367 and older/unrelated programs do not honor it. Java file locking behavior may depend on the host filesystem; there is no tested power-loss/fsync guarantee, multi-file transaction for `order.settings`/version markers, or original client login/reconnect/GUI rendering acceptance. The UI callback is verified using an isolated panel stub; the real `LoadoutsPanel` class compiled but **has not been visually launched**. This is a **private test candidate, not a release-ready patch**.

**Source release gate CLOSED.** No changes to live v312, signed updater, original v309 binary, existing caches or real game servers.
