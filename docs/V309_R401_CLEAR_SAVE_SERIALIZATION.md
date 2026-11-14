# R401 — serialize clear-all and history writes, reject stale save generations

**Repository:** Trexzo/SpawnPK-Client
**Stacked on:** R400 draft PR #1196
**Status:** DRAFT / UNMERGED. Private source release, runtime execution,
production installation and distribution all remain CLOSED.

## What the owner-private source review established

The R400 Loot Tracker persistence path allowed two operations to race:
an ordinary history save could snapshot old panel rows, then a user could
choose **Clear all** and delete the history file, while the earlier save
could complete afterward and recreate the deleted contents.

The store's original void \`clear()\` also swallowed I/O errors.
The plugin had no success acknowledgement and cleared its panel even if
the disk delete failed.

Other operations are **not** fixed by this patch:
\`LootTrackerPanel.removeSource\`, \`removeType\` and \`removeRecord\`
modify the panel independently and call \`persistHistory()\`, without
the R400 handoff version covering their changes. Concurrent saves
could still reintroduce removed rows. These are known open risks,
not claimed resolved.

## Experimental owner-private R401 implementation

A new isolated candidate was copied from R400; only these two owner-private
files changed:

- \`rs/plugins/loottracker/LootTrackerPlugin.java\`
- \`rs/plugins/loottracker/LootHistoryStore.java\`

The candidate adds a per-plugin \`r401FileGate\` monitor for confirmed
file writes, early-shutdown history commits and clear-all deletion.
It also tracks a clear generation and clear-in-progress/unsafe states.

**Normal save:** the accepted panel/pending snapshot carries the exact
clear generation. After acquiring \`r401FileGate\`, the save rechecks
that generation under the existing history monitor before overwriting
disk. On success it rechecks again before acknowledging committed
pending entries. A clear that occurs between snapshot and writer lock
invalidates the old save; a clear started while a write owns the file
lock waits for that write and deletes afterward. No EDT
\`invokeAndWait\` was introduced.

**Pre-restoration shutdown merge:** a merge captures the clear generation
before its strict history read, revalidates it while holding the same
file monitor before commit and again before acknowledging success.

**Clear all:** the call is applied on the Swing EDT. Off-EDT callers
are requeued without blocking the client thread on
\`invokeAndWait\`. A clear increments the generation and invalidates old
drop callbacks before acquiring \`r401FileGate\`. The history file
deletion now returns a boolean success receipt, with missing-file
treated as success. I/O and security-permission exceptions return
failure. If deletion fails, the old panel remains visible and
automatic saves become fail-closed until an explicit successful clear.
If deletion succeeds, the panel is cleared synchronously on the EDT
rather than leaving an unscoped stale \`invokeLater(panel::clearRecords)\`
callback that could erase new records later.

The owner-private storage class keeps its legacy void \`clear()\`
entrypoint, delegating to \`clearWithReceipt()\`, for compatible callers.

## Verified owner Windows evidence

- Full JDK21 \`javac --release 11\` compilation:
  **1,277 source files → 1,388 class files**, exit 0.
- Exhaustive class byte comparison vs R400:
  **exactly two changed classes** — \`LootTrackerPlugin.class\` and
  \`LootHistoryStore.class\`. Comparison with R381 still differs
  only in those same two classes. Neither the private golden source
  archive nor the older R400/R399 candidates were modified.
- Public read-only, SHA-pinned verifier run over the final owner-private
  source/class trees: **\`R401_PRIVATE_CLEAR_SAVE_STATIC_GATE_PASS\`**
  (exit 0). The gate checks exact two-source/two-class scope,
  clear-generation barriers, common file monitor, delete-success
  receipt, security error behavior, EDT panel-clear ordering,
  fail-closed branches and no detected history→file lock inversion.
- **30/30** public synthetic Python positive/negative tests passed
  locally. **17/17** standalone JDK11-compatible Java synthetic
  clear/save/merge interleaving tests passed locally. One includes two
  real Java threads, blocking a mock disk writer while clear competes
  for the same lock. The tests use invented in-memory records only.
- Private candidate JAR is retained on the owner's isolated TEMP
  workspace as \`R401-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`:
  SHA256 **e6958e4865e7adcf437d1fef91d22ac7e2507577289427ad34d57da204e3f345**.
  It was packaged but **not executed, deployed, uploaded, shared
  or installed**.

## Explicit safety, concurrency and performance limits

This is a narrow clear-vs-save source fix, not a comprehensive
transactional storage layer. The monitor exists only inside this plugin
instance, not as an OS-enforced cross-process lock. Separate plugin
instances or processes may still write the same \`.tmp\` history path.
The storage move does not constitute proof of power-loss durability.

No actual client, Swing event queue, game packets, user history, or
private runtime was executed or modified. A real client freeze root
cause, original-v309 behavior parity, v312 compatibility, cross-process
writer safety and all race interleavings remain unverified.

A new drop can still arrive while clear is in progress. Clear-all
semantics for such in-flight events need a separate end-to-end test,
especially when the UI event queue is busy. Direct removal of one row,
source or loot type remains unversioned and can race a save.

The R397 synthetic journal remains separate research; R401 did not
change the current history format, introduce event IDs, or implement
crash recovery. The potentially expensive synchronous dirty-shutdown
I/O can still block the Swing EDT.

Do not merge, run, release, install, distribute or authorize live
cleanup. No independently verified non-egress guest with immutable
production mounts is established.
