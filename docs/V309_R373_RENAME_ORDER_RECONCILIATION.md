# R373 — source-backed rename recovery: `order.settings` consistency

**Correct repository:** `Trexzo/SpawnPK-Client`. Stacked on draft R372 PR #1167. This is **private reconstructed v309 candidate source**, not a change to the live client. Keep **DRAFT/UNMERGED**.

## Reproduced R372 defect

A verified rename intent can be replayed after destination file creation, deleting the old folder and its receipt, while the persistent `order.settings` file still contains the old name. R372's next folder discovery notices the new file and appends it to its in-memory list, but the persisted order remains stale. An actual recovered-source Java fixture confirms **R372 FAIL: `STALE_ORDER_ENTRY`**.

## Bounded private R373 repair

Only `rs/gui/loadouts/io/LoadoutStore.java` changed (one of 1,277 Java sources). After validating the rename receipt and checking the raw hashes of source/destination under the existing ordered cooperative folder locks, but **before deleting the old folder**, recovery:

- Acquires the **same** persistent `.loadout_order_lock.lck` used by normal order writes.
- Rejects symlinks, nonregular or oversized `order.settings`, undecodeable bytes, duplicate old/new references and conflicting entries.
- Replaces exactly the old folder name, preserving all other names, order and line-ending bytes, using a staged file, final fingerprint check and atomic rename (no nonatomic fallback).
- Treats an already-reconciled order file as an idempotent retry. If there is no settings file, discovery retains the normal legacy behavior.
- On refusal retains **both folder files and the rename receipt**, rather than deleting anything on unverified metadata.

The existing R372 receipt and version-marker protections remain. Ordering and folder data are **not** a single atomic transaction; stage and receipt directory `fsync`, power-loss crash durability and uncooperative writer exclusion are **not proven**.

## Owner-private evidence, not hosted CI

- R372 archive SHA256: `582bd22720fa6655b8082d83ec69f01f9073f1e79eb0ddf225eccab00d441e4b`.
- R373 archive SHA256: `c87c7e2158437f03c3f52e1d88f2c91a6e9949bedc9e74917b50d30186b67e67`.
- R373 deterministic JAR SHA256: `7154b4dd2a6609feb29fc01596a788ed413bc6f5b935d9ceefd4b3af92a2480a`.
- **45/45** new Java order-recovery assertions PASS; R372 baseline fails the stale-order assertion as expected.
- **233** inherited assertions PASS: R372 rename (56), R371 rename (16), version receipt (29), loadout store (44), order settings (28), serializer (60).
- `javac --release 11` on OpenJDK 21: **1,277 sources → 1,388 `.class` files**. Independent rebuild from a fresh private build-kit extraction reproduced identical JAR SHA256.
- All source manifest digests checked. Only `LoadoutStore.java` differs from R372.

## Public verification scope and release gates

The public PR contains only this report, a source SHA witness, an offline verifier, **21 synthetic Python tests**, and four hosted Windows/Ubuntu Python 3.11/3.13 CI jobs. Hosted CI **does not compile proprietary Java code or prove real game runtime behavior**.

Not tested: original v309 JAR parity, real GUI launch/login/reconnect, v312 compatibility, actual owner caches, interprocess non-cooperative writers, real power loss, directory-fsync durability and complete multi-file atomic transactions. **Source-M1 release gate CLOSED. No production promotion.**
