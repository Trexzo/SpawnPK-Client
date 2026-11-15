# R421 — cache-path provenance and guarded one-level directory preparation

**Repository:** Trexzo/SpawnPK-Client
**Parent:** R420 draft PR #1216
**Status:** DRAFT / UNMERGED. Private game execution, production writes and release gates CLOSED.

## Source finding: cache directory was already created upstream

R420's `new LootHistoryStore()` called `Class307.method121()`. The latter is a **game-global** cache path resolver, not Loot Tracker-only. It computes the cache name from `Configuration.field1268` (SpawnPK or Runex), `isTestBuild`, `field1256` and `user.home`, then uses a preexisting `mkdir()` branch or returns null. That means a missing cache directory may already have been created as a *startup side effect* before the R420 background writer lease was acquired; checking only inside `r418TryAcquireCooperativeLease()` did not address that earlier creation or an unexpected invalid parent.

**R421 changes only Loot Tracker's use of that path.** It does not modify `Class307.method121()` or its other callers, and does not claim to remove every other startup directory creation in the game.

## Actual isolated owner-private R421 candidate

Created a fresh `R420-Private-Bounded-Lease-Retry/Source-Candidate-R420` successor:

`SpawnPK-R386-Isolated-Acceptance/R421-Private-NoFollow-Cache-Directory-Preflight/Source-Candidate-R421`

Exactly two private files changed:

- `rs/plugins/loottracker/LootHistoryStore.java`
- `rs/plugins/loottracker/LootTrackerPlugin.java`

`LootHistoryStore()` now delegates to `r421CacheLocationWithoutCreation()` instead of calling the global `Class307.method121()`. It computes the same expected SpawnPK/Runex cache paths for standard/test configurations and the same relative `./cache/` developer-mode path, but performs no directory creation. It refuses a null home directory or unsafe cache identifier rather than falling back to an ambiguous path.

The store adds a package-private `r421PrepareHistoryDirectoryForLease()`. This:

- Resolves and normalizes the history parent on the background restore worker;
- Requires **every existing ancestor** to be a real directory under `NOFOLLOW_LINKS`, not a symlink or other special file;
- Accepts an already existing real directory after a before/after identity recheck;
- For an absent final leaf only, calls `Files.createDirectory()` **exactly once**, never recursive `mkdirs` and never creates a missing ancestor;
- Refuses concurrent `FileAlreadyExistsException` collisions and uninspectable paths without deleting, replacing or cleaning any file;
- Checks parent metadata identity again after creation. It never touches loot history, intent, acknowledgment or staging payloads.

The plugin invokes this check **only from** the R420 bounded retry helper on the background restore worker, *after* verifying that the current plugin, store, session and generation remain valid and prior to any lock acquisition or retry sleep. R420's per-attempt session checks, nonblocking `FileChannel.tryLock`, and R419's history write/read admission gates remain intact.

**Important security limitation:** This is a defensive local path preflight, **not an anchored race-proof directory operation**. A malicious/non-cooperative process controlling an ancestor might replace it between no-follow metadata checks and `Files.createDirectory`. It also cannot disable the game-global resolver used elsewhere. Do not claim hostile-writer protection.

## Actual owner Windows evidence

- JDK21 `javac --release 11`: **1,277 Java sources → 1,394 compiled classes PASS**.
- Exhaustive R420→R421 byte-for-byte source/class inventory: exactly two changed sources and **exactly two changed existing classes**: `LootHistoryStore.class` and `LootTrackerPlugin.class`; no added, removed, or unrelated changed classes.
- SHA256 source pins:
  - Prior store: `3de16fab8f734846dc13d32cd55e3845387298d881c03de2701a7b4120309e79`
  - R421 store: `0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29`
  - Prior plugin: `844451db7874ff54eb90cd5ccc93591624bd33a3b8a6e5c13e3a60787b923c3d`
  - R421 plugin: `725352a08b8b67a24f70b8d53a7c82bc31bcb7531acfd2adfe17876ff2fb21c2`
- Read-only SHA-pinned auditor run on the *actual owner-private* source/class trees: **`R421_OWNER_TEMP_DIRECTORY_PREFLIGHT_STATIC_GATE_PASS`**, exit 0. No private code or class bytes were published.
- No private game client was launched, no production v312 file/history/credential/cache was read or changed, no JAR was packaged, and no installation or release was authorized.

## Independent public-only synthetic tests

This branch publishes only independently invented Java/Python TEMP-filesystem tests, a read-only source/class auditor, CI and documentation.

- `tests/fixtures/r421/R421CacheDirectoryModel.java` models one-level creation and no-follow path inspection against invented temporary roots and independently derived cache paths.
- `tests/test_v309_r421_cache_directory.py` checks missing/existing leaf, parent and leaf symlinks, regular-file collisions, missing ancestors, race among multiple Java subprocesses, preservation of fabricated history/intents/acks, path versions and no-create derivation.
- `tools/r421/audit_private_directory_preflight.py` verifies the exact two-source/two-class R420→R421 owner-private SHA-pinned delta, background-only preflight, constructor safety, nonrecursive single-leaf creation and the absence of file cleanup.
- `tests/test_v309_r421_directory_audit.py` supplies 25 fabricated source-mutation negative controls for nofollow removal, recursive mkdir, extra cleanup, unsafe constructor fallback, missing session check, metadata identity bypass and unexpected class/source drift.

A typo in the new audit test name initially prevented that test module from importing; it was fixed. The **final local Windows JDK21/Python3.12 suite** then passed **55 tests, 53 PASS, 2 optional symlink SKIP, 0 FAIL**.

The hosted Windows/Ubuntu x Python 3.11/3.13 JDK21 matrix is independently checked after the final PR commit; do not infer hosted success from local results alone.

## Outstanding blockers

1. The global `Class307.method121()` still has the original `mkdir()` / null behavior elsewhere in the game; R421 covers only Loot Tracker's constructor, not other global cache owners or unsafe path-change races.
2. No original-client runtime acceptance and no actual Java/Swing callback interleaving proof. Private source compiles but its UI and persistence startup contract is not validated in a live client.
3. R420's bounded busy-lock retry can still exhaust; neither R420 nor R421 authorizes an unbounded retry or automatic history overwrite.
4. Confirmed deletions, Clear all and final shutdown persistence may still perform disk I/O synchronously on Swing's EDT. No FPS gain or original freeze fix established.
5. R415–R417 journal evidence continues to quarantine normal writes; there is no safe automatic history adoption, marker cleanup, acknowledgment or reenable protocol.
6. Lock-path replacement, hostile/noncooperative writers, power-loss directory-fsync, deployed v312 compatibility and original-game startup freeze remain unverified.

**Keep R421 draft, unmerged and owner-private. Do not deploy or distribute a private build.**

**Proposed R422:** isolated lifecycle/fault-injection test of the actual reconstructed Java store and plugin admission paths (rather than only structurally modeled Java), focusing on shutdown/restore interruption, stale-session callback races and rejection of path/journal conflicts. Plan the EDT-safe confirmed-deletion receipt protocol only after those passes.
