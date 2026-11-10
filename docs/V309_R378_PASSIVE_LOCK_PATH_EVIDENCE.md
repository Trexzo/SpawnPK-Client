# R378 — passive lock-path evidence for loadout staging diagnostics

**Repository:** `Trexzo/SpawnPK-Client`, stacked on R377 draft PR #1172.
**Private source release gate CLOSED. Keep draft and unmerged.**

## What the genuine recovered private source supports

R377 already inventories stage candidates with no-follow age/size metadata. R378 adds a **read-only** correlation for the known order staging prefixes (`.loadout_order_stage-*` and `.loadout_order_rename-*`) and the persistent `.loadout_order_lock.lck` **path**. Order-lock path metadata is obtained with `Files.readAttributes(..., NOFOLLOW_LINKS)`, never by opening a lock channel or calling `tryLock`. Other randomized stage names **cannot be mapped to a particular folder lock** and are reported as unknown. Unsafe stages never receive a lock association.

`ORDER_LOCK_PATH_PRESENT_HELD_UNKNOWN` means the file path exists; it does **not** mean another process holds a Java lock. Its presence is persistent after the writer exits. The same label was observed both with a real held `FileLock` and after releasing it. Missing, unsafe, and unavailable lock paths are also non-conclusive about writer activity. No payloads were read; no stages, receipts, locks or user data were deleted or changed.

## Verification

- SHA-pinned genuine recovered R377 source ZIP `febb2e92f1588d5f346414a4166de01d881086dc4bfd57fb728b25d493e70074` to R378 source ZIP `65d331e4cd6a0ef51fa7620e89548c7001e008e64a67a5ef1d6bd4e371e0a9b1`. **Exactly one of 1,277 Java source files changed**, `LoadoutStore.java`.
- **28 new scratch source-backed Java assertions PASS**. **382 inherited source-backed assertions PASS**, including R377/R376, rename recovery, ordering, locks, versions and serializer tests.
- OpenJDK21 `javac --release 11`: **1,277 Java sources → 1,388 class files**, clean compile. Full clean build-kit replay reproduced JAR SHA-256 `39c77d764285dc9ae908d63d9014e6eb497f6c3ed7077f74eca17a7780576cec`.
- Public Python synthetic archive verifier and generic Windows/Ubuntu Java lock-metadata probe test only synthetic data, not recovered source or game execution.

## Explicit limitations

Neither stage age nor persistent lock file existence proves a writer is active or inactive. No active process identification, no cross-process ownership resolution, no cleanup, no original-client login/GUI execution, no original JAR parity, no Windows private source runtime test, no multi-file atomicity or power-loss durability proof. Original v309 binaries, production v312/updater and user caches unchanged. Keep **DRAFT/UNMERGED**.
