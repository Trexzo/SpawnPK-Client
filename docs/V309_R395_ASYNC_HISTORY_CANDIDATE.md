# R395 — private async Loot Tracker history-restoration candidate

**Repository:** Trexzo/SpawnPK-Client. **Stack base:** R394 draft PR #1190.
**DRAFT/UNMERGED; owner-private Source-M1 release gate CLOSED.**

## Status: experimental private candidate, not a production fix

A genuinely modified, rebuilt private source candidate exists ONLY in an
isolated TEMP workspace on the authorized owner Windows device. It is not
committed to GitHub and must not be distributed to friends, the live v312
client, launchers or updater. The public PR contains only a read-only
candidate verifier, synthetic Java/Python tests, CI and this metadata.

The owner-local path relative to the earlier isolated root is
\`R395-Private-Async-Restore/\`. It holds an untouched SHA-pinned original
source ZIP; a disposable, independently extracted private candidate tree;
a private-only transformation script; compilation output and reports; and
\`R395-PRIVATE-DO-NOT-RUN-Candidate.jar\`. The private JAR is **not
authorized for game execution**, use by friends, or upload.

## Source-level behavior of candidate

- A one-shot daemon worker is created during requested history restoration,
  moving \`LootHistoryStore.load()\` (file read/JSON parse) from the Swing
  event-dispatch thread (EDT) to the worker.
- Its results are applied using Swing \`invokeLater\`, guarded by the
  original plugin/panel/store identity and a monotonically changing
  generation. Repeated requests while loading coalesce.
- \`persistHistory()\` defers saves while initial restore is incomplete.
  The old file remains unchanged instead of being overwritten with a
  partial/empty panel. The deferred write is attempted once restoration
  has successfully applied.
- \`clearHistory()\`, plugin stop and next startup invalidate callbacks
  issued by an earlier generation. Pending live drops are NOT cleared
  in the restoration callback; live-drop callbacks manage their own
  in-flight identity on the EDT.
- Failure to parse history leaves the source file unchanged and does not
  mark history as successfully restored. A later authorized loading
  request may retry.

This source change is an intentional startup behavior experiment; **it
must not be described as proving original-v309 behavioral parity.**

## Real owner-Windows static compile and class-difference evidence

The original owner-private R381 source ZIP was verified at SHA-256
\`902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96\`.
A copy of its 1,277 Java sources was extracted only into the isolated
R395 TEMP candidate workspace. Exactly one private source file was
edited, \`rs/plugins/loottracker/LootTrackerPlugin.java\`.

Windows JDK21 \`javac --release 11\` compiled **1,277 / 1,277** source
files to **1,388** class files, exit 0. A direct byte comparison of all
1,388 classes with the owner-private R381 reference JAR
(SHA-256 \`ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3\`)
found **exactly one changed class**:
\`rs/plugins/loottracker/LootTrackerPlugin.class\`.

A dedicated R395 read-only, SHA-pinned delta verifier additionally
checked original/candidate source and class sets, exactly-one-file
change scopes, named method/barrier structure and stale-result guards.
Exit 0, \`R395_PRIVATE_CANDIDATE_CLASS_SCOPE_PASS\`.
A private archive was assembled solely for offline custody; its SHA-256:
\`efcb5b9e32ec0c6a30eda73cf2e8dccad0933cf6db05c5df975df260a6de0526\`.

**No Launcher.main, Client.init/start, plugin startUp, private jar,
network connection or actual GUI was executed.** The golden R381 source
ZIP and live v312 source/client/updater/cache/server were not modified.

## Public tests and scope

- **22** synthetic Python checks passed on owner Windows Python 3.12,
  covering SHA pin drift, source/class set changes, symlinks/traversal,
  refusal to overwrite reports, save deferral, clear/stop invalidation,
  duplicate scope and source/no-leak guards.
- **11** standalone JDK11-compatible Java race-model checks passed
  on owner Windows/JDK21. They exercise deferred saves, new drops during
  loading, preserving in-flight drops, duplicate-load coalescing,
  clear/stop/restart invalidation, failure and retry, empty history,
  and a **real headless Swing EDT responsiveness check** with a blocked
  synthetic background reader.
- CI runs these synthetic-only fixtures across Windows+Ubuntu and
  Python 3.11+3.13 with Temurin JDK21. There are no private bytes in CI.

The synthetic Java model reproduces important concurrency contracts; it
is NOT the actual recovered LootTrackerPlugin and therefore cannot prove
the private compiled class behaves identically under runtime races.

## Explicit unresolved release blockers

1. **Early shutdown and unsaved live drops:** stopping the plugin while
   background restore is unfinished invalidates the stale callback and
   preserves the existing on-disk history, but **does not guarantee
   durability of live drops received during that window**. Fix and
   test this before release. Do not claim zero data loss.
2. The EDT still does \`panel.addRecords\`/aggregate rebuild and may
   perform a deferred history write. Moving JSON parsing off the EDT
   alone does not prove total startup latency or full UI responsiveness.
3. Real private runtime integration, plugin disable/re-enable timing,
   file/directory races, error and cancellation paths, resource cleanup,
   native game startup and original-v309 parity remain unverified.
4. A disposable guest with independently proven network egress denial
   and no writable production mounts is required before real startup
   tests. A custom \`user.home\` property is not enough.

All gates explicitly remain \`launch_authorized=false\`,
\`private_source_release_approved=false\`, \`merge_approved=false\`,
\`shutdown_during_restore_durability_proven=false\`,
\`real_runtime_race_acceptance_proven=false\`. Leave DRAFT/UNMERGED.
