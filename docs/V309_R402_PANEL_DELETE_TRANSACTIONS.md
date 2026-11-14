# R402 — serialize panel source, type and individual-record deletion

**Repository:** Trexzo/SpawnPK-Client
**Stacked on:** R401 draft PR #1197
**Status:** DRAFT / UNMERGED. Private source and runtime release CLOSED.

## Identified source race

R401 protects **Clear all** against a concurrently executing history
save, but three other panel mutations were still uncoordinated:

- Delete a source/group using \`removeSource\`.
- Delete all records of one type using \`removeType\`.
- Delete a single record by **object identity** using \`removeRecord\`.

Each originally modified \`LootTrackerPanel.records\`, rebuilt the
view, then called \`plugin.persistHistory()\` with no file-gate
coordination around the panel mutation. An ordinary save that had
captured the older panel snapshot could write after a deletion and
resurrect the removed record(s). The store's record equality considers
source/type, so removing by equality could also delete the wrong one
of multiple identical-looking drops.

## Actual isolated owner-private R402 candidate

This candidate copies R401 into a new owner TEMP directory and changes
**only**:

- \`rs/plugins/loottracker/LootTrackerPlugin.java\`
- \`rs/plugins/loottracker/LootTrackerPanel.java\`

All three confirmed deletion methods now call the plugin's common
\`r402ApplyPanelDeletion(Runnable)\`. The existing confirm dialogs stay
outside the transaction; the selector, panel mutation, aggregate
updates and rebuild run inside it.

The plugin requires a valid Swing EDT and loaded, reconciled history,
then obtains the existing R401 **file-operation gate** before mutating
the panel. It increments the history edit generation and marks the edit
in progress under the history monitor, releases that monitor before
running the Swing mutation, then increments the generation again.
An ordinary save taken before either edit transition must recheck
the generation before commit; snapshots taken mid-edit are refused.
A save already holding FileGate completes before the edit can start.

The shared file monitor is held through the panel mutation and the
following \`persistHistory()\` commit, which is reentrant on the same
Java monitor. The plugin captures a positive disk-write receipt from
the successful save; if the mutation throws or the write is not
acknowledged, it marks history unsafe and refuses automatic writes
rather than silently claiming the user deletion was persisted.

When \`rememberLoot\` is disabled, deletion remains a **UI-only**
operation, matching the earlier behavior; it does not require a
disk-write receipt.

A deleted single record continues to use reference identity
(\`r == record\`), preserving independent duplicate-looking drops.

## Local verification completed on owner Windows

- Full **JDK21 javac --release 11** compilation:
  **1,277 private Java sources → 1,388 classes**, exit 0.
- Exhaustive class byte comparison with the prior R401 private build:
  exactly **two class files changed**:
  \`LootTrackerPlugin.class\` and \`LootTrackerPanel.class\`.
  Compared with the SHA-pinned R381 corpus, only those classes plus
  the existing \`LootHistoryStore.class\` differ.
- Read-only SHA-pinned verifier executed on the **actual private**
  source/class candidate:
  \`R402_PRIVATE_PANEL_DELETE_STATIC_GATE_PASS\`, exit 0.
  It checks the two-source/two-class delta, each deletion selector,
  paired generation increments, lock order, the save-time mutating
  guards, confirmed receipts and explicit fail-closed paths.
- **24/24** synthetic Python gate/negative-control tests passed
  locally; **16/16** standalone synthetic Java interleaving
  scenarios passed, including a genuine two-thread test where
  a deletion competes for the file-operation gate with an old save.
- Private custody-only JAR
  \`R402-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`:
  SHA256
  \`7667621c2aa2a3d624aac7e69d56412d06a40653cd198a2e93696b29394a4e4b\`.
  It remains under the isolated owner TEMP workspace. It was **not**
  executed, installed, uploaded or distributed.

## Important remaining limitations

The design intentionally prioritizes not resurrecting deleted records;
**it does not improve the existing UI freeze risk** from synchronous
disk writes. A pending save can still hold the file gate while the
Swing EDT waits to perform a confirmed deletion, and rendering plus
the edit's save also occur while the EDT holds that gate. Moving
persistence off the client/EDT thread requires a separate, carefully
tested queue, durability protocol and transactional edit acknowledgment.

If a deletion's disk commit fails, the in-memory panel can differ
from the persisted file. The candidate logs and quarantines automatic
writes, but cannot automatically restore the unsaved edit across
process termination. Explicit Clear all can reset the quarantine;
it is a destructive recovery path, not a user-friendly retry UI.

Other code may still mutate panel-derived state without this
transaction. Cross-process and multiple-plugin-instance writes are
not serialized by the per-instance monitor. No durable event IDs,
integrated journal, verified real-client runtime races or power-loss
durability are established. The R397 journal remains a standalone
synthetic research model.

All checks were isolated private static builds and public invented
synthetic tests. No real game client, user loot history, live v312
installation, friend package or production update was executed
or modified. Original v309 parity, current v312 compatibility, and
root cause of the original client hang are not proved. No
independently verified network-isolated guest with nonwritable
production mounts is established.

**Keep draft, unmerged. No private source release or client launch
authorized.**
