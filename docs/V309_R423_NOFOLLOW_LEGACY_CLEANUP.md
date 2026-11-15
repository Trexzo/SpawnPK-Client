# R423 — no-follow legacy cleanup research and owner-private risk gate

**Repository:** Trexzo/SpawnPK-Client
**Parent:** R422 draft PR #1218
**Status:** DRAFT / UNMERGED. PRIVATE CLIENT **NOT PATCHED**. Release gate CLOSED.

## Concrete risk confirmed

In the owner-private isolated R421 `LootHistoryStore.java`, `r419DeleteStaleLeased()` eventually calls `deleteTree(parts)` for the retired `loot-history` directory. The actual private `deleteTree(File file)` implementation calls `file.listFiles()` recursively, then `Files.deleteIfExists(file.toPath())`. There is no explicit `NOFOLLOW_LINKS` guard inside the recursive walker. A local independent JDK21 synthetic probe confirms that calling `java.io.File.listFiles()` on a directory symlink enumerates a file **outside** the intended legacy tree. Therefore the existing recursive code should **not** be treated as a safe bounded cleanup when symlink or special-file entries are possible.

R419's cooperative lock, R411's outstanding-stage fence and R421's parent directory preflight do not change `File.listFiles()` recursion semantics. The hazard is conditional on unsafe entries or filesystem manipulation; there is **no evidence that any user data was actually deleted or affected by this hazard**.

## Public-only candidate policy

The repository now contains an independently authored Java 11 research model:

`tests/fixtures/r423/R423NoFollowLegacyCleanup.java`

It operates **exclusively** on already-existing direct children of the JVM TEMP folder whose names start with `R423-Synthetic-`. No game classes are imported or executed, and the code is NOT a replacement for the private client without independent integration work.

The model illustrates a safer cooperative policy:

- Require a held, nonblocking `FileChannel.tryLock` on a persistent writer-lock path. Reject unleased and competing processes; never unlink the lock file.
- Refuse any outstanding `loot-history.json.tmp`, delete-intent, intent stage, acknowledgment or acknowledgment stage *before* legacy cleanup. Check again immediately before each deletion.
- Perform a **complete read-only** two-phase `Files.walkFileTree` preflight with no `FOLLOW_LINKS`: reject symlink files/directories, unexpected file types, missing/unreadable components, a too-deep tree (16 levels), more than 4,096 entries or oversized individual files (64 MiB).
- Preflight both retired paths, `loot-history/` and `loot-keys-seen.txt`, **before deleting either**. A symlink in the seen-keys file therefore cannot trigger partial cleanup of a safe legacy tree.
- Recheck all parent directories with `NOFOLLOW_LINKS`, file metadata identity and journal evidence immediately before deleting each postorder entry.
- Preserve the canonical `loot-history.json` and unrelated root files. Neither preflight nor cleanup touches other named data.
- Refuse UI-thread cleanup, interrupted workers and unknown filesystem states. On an error partway through cleanup, stop immediately with an explicit `PARTIAL` result; **do not claim rollback**.

**Critical limitations:** This model is not an anchored/openat-style race-proof defense against a hostile process swapping ancestor path components, nor is a file lock protection from noncooperative writers. If a failure or interruption happens after one or more deletes, earlier deletions remain; journal reconciliation and rollback are not implemented. Such files need explicit recovery semantics before production use. Large legitimate retired trees exceeding the conservative caps fail closed.

## Independent public validation

- Local Linux JDK21 `javac --release 11` completed successfully.
- **42/42 synthetic Python-driven Java tests passed locally**; they use actual TEMP files, actual competing JVMs/FileLocks and simulated crashes.
- Tests cover safe ordinary legacy cleanup, dry-run/idempotence, unrelated/canonical history preservation, symlinked root/child/file/seen-keys paths and external sentinels, unsupported special-file types, absent-owner/busy-owner/crash/reacquire, 4,096-entry and 16-depth caps, oversized files, unresolved journal evidence and journal introduction **after** preflight, interrupt before/after partial deletion, and a symlink replacing the first planned file **after** preflight.
- The Java headless mode is explicitly enabled in subprocesses so hosted Linux runners without a graphical X11 server do not fail for unrelated Swing toolkit reasons.
- `tools/r423/audit_private_legacy_cleanup.py` is an **owner-opt-in, SHA-pinned read-only** inspection of the exact R421 private source. It reports `R423_PRIVATE_RECURSIVE_SYMLINK_RISK_REVIEW_REQUIRED` only when the old recursive shape and lease/stage caller are present; a source mismatch refuses rather than reporting safe. `tests/test_v309_r423_audit.py` has **18 synthetic negative controls** for the static audit.
- Hosted Windows/Ubuntu × Python 3.11/3.13 JDK21 matrix is separate and must be independently checked before claiming hosted success.

### Owner-private source pin

The last owner-private R421 `LootHistoryStore.java` SHA-256 is:

`0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29`

A future owner-local risk check can run the public audit by specifying the **exact** source path and `--expected-sha256`. Do **not** run any cleanup tool on a real history path to perform this audit. The auditor only reads source text.

## Deployment, scope and next work

Remote Desktop Commander has reached its monthly usage quota, so **R423 has not modified or compiled any private Java source/class**. It has not accessed live v312, opened real loot history, launched a game client, constructed a private JAR, distributed files, or authorized a marker cleanup.

**Do not merge or deploy R423.** The next owner-private integration stage must replace (not merely wrap) the old recursive `deleteTree(File)` path with a source-reviewable no-follow implementation, give it a precise transaction and partial-failure contract, compile it with `javac --release 11`, verify an exact class-byte scope, and test actual private store behavior on only invented TEMP histories. The restarted cross-process R422 acceptance and actual Swing lifecycle checks also remain incomplete.

The original EDT-blocking Clear all and confirmed-delete code still needs a separate asynchronous receipt design; no FPS or frozen-window improvement is claimed here.
