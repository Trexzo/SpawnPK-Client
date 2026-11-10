# R379 — cooperative order-lock contention observation (private candidate)

**Repository:** `Trexzo/SpawnPK-Client`. **Base:** draft R378 PR #1173. **Release gate CLOSED; keep DRAFT / UNMERGED.** Production v312, original v309 binary, updater, credentials, cache and servers were neither accessed nor changed.

## Source-backed finding

R378's passive lock-file metadata is identical whether a lock is actually held or idle. R379 adds a **nonblocking observation of the existing order lock** for only the recognized `.loadout_order_stage-*.pending` and `.loadout_order_rename-*.pending` stage names. The new method in private `rs/gui/loadouts/io/LoadoutStore.java` first checks `.loadout_order_lock.lck` with `NOFOLLOW_LINKS`, then attempts `FileChannel.tryLock()` **without `CREATE`**. It immediately releases a successfully acquired lock.

- `ORDER_LOCK_BUSY_AT_OBSERVATION_OWNER_UNKNOWN` means momentary cooperative contention, **not identification of the writer or stage owner**.
- `ORDER_LOCK_FREE_AT_OBSERVATION_OWNER_UNKNOWN` means the check temporarily acquired the lock, **not that any staging file is orphaned or safe to delete**.
- Missing, unsafe, inaccessible or unsupported lock paths have their own explicit results.
- Randomized folder/version/rename stage files retain `FOLDER_LOCK_OWNER_UNKNOWN_NO_PROBE`. Unsafe stage candidates are not probed.

Observation can become stale immediately; older/uncooperative clients may not use these locks. This is a diagnostic only: **no staged payload reading, no lock creation, no automatic cleanup, and no owner identification**.

## Owner-private verification (not hosted CI)

Only **one** of the SHA-pinned **1,277 recovered Java sources** changed: `rs/gui/loadouts/io/LoadoutStore.java`. Full private OpenJDK21 compilation using `javac --release 11` produced **1,388 classfiles**. A fresh build-kit extraction independently rebuilt the identical candidate JAR SHA-256:

`1d57ea243770e9b112256ff7297c701fd8f76ac2ca2af4d41fcf1f9ce21dba65`

**32** new scratch-only source-backed Java assertions passed, including a held lock in a real second JVM, same-JVM overlap, released lock, absent/unsafe/symlink lock path, and stage preservation. **410** inherited source-backed assertions passed across the earlier recovery and serializer suites. SHA-pinned previous source ZIP `65d331e4cd6a0ef51fa7620e89548c7001e008e64a67a5ef1d6bd4e371e0a9b1` → R379 `e23d2483b0acd27939e6b467ae6bf4e8b9f25652f57d3523fe93c32f8bb523ca`.

## Public verification and boundaries

The PR includes **six public-safe files only**: this report, source-delta witness, Python SHA verifier, **38 synthetic Python tests**, GitHub Actions Windows/Ubuntu workflow and a generic JDK21 scratch-only lock probe. Hosted tests **do not compile or execute proprietary client sources**; the generic probe may legitimately report a provider unsupported result.

**NOT PROVEN:** original client parity, actual Windows private-client runtime, lock-owner identity, stage cleanup safety, physical power-loss fsync durability, multi-file atomicity, real login/reconnect, or v312 compatibility. **Do not merge, release or delete staging evidence based on these diagnostics.**
