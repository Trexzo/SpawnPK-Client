# R407 — clear-all/autosave epoch admission recovery

**Repository:** Trexzo/SpawnPK-Client
**Stacked on:** R406 draft PR #1202 (passive contention evidence)
**Status:** DRAFT / UNMERGED, private source and runtime release CLOSED.

## Source-confirmed regression fixed in the isolated candidate

R406 identified a conditional dead state in the R403–R405 background
autosave queue:

- \`r403QueueAutosave()\` sets \`r403AutosaveQueued=true\` after accepting
  a task for the current plugin session. Further requests only set the
  coalesced dirty flag.
- \`clearHistory()\` increments \`r399SessionEpoch\` to invalidate older
  drops and saves but previously did **not** clear the queue/dirty flags.
- A worker's \`finally\` is intentionally forbidden to reset those
  flags after its captured epoch becomes obsolete.
- Consequently Clear all during a queued/in-flight save could leave
  \`r403AutosaveQueued=true\` indefinitely, preventing newly received
  loot from starting an autosave in the same plugin instance.

R407 is a **narrow one-source fix**, not an asynchronous deletion rewrite.

## Owner-private R407 implementation

A fresh isolated owner TEMP copy of the R405 source tree changes only
\`rs/plugins/loottracker/LootTrackerPlugin.java\`. R406 had no source
changes, so R405 remains the exact prior private build.

1. \`clearHistory()\` now resets \`r403AutosaveQueued\` and
   \`r403AutosaveDirty\` **inside the same \`r395HistoryGate\` critical
   section as \`++r399SessionEpoch\`**, after marking clear in progress.
   No interrupt or executor shutdown is introduced. An old task that
   was queued before the clear cannot write after it: the R403
   captured-epoch check inside the R401 file-operation gate remains in
   place, and old jobs' \`finally\` handlers cannot clear a newer
   session's queue state.
2. The worker's initial **acceptance/epoch check and
   \`r396LastCommitSucceeded=false\` reset** are now one history-gate
   transaction rather than two separate synchronized blocks. Thus
   an old worker cannot pass admission, yield to Clear all, then reset
   a shared receipt bit while a new session is active.
3. An exception from an old autosave worker can no longer set
   \`savePending=true\` after Clear all, a plugin restart or an unsafe
   failed deletion. The exception retry is guarded by epoch, active
   plugin identity, drop admission and clear/unsafe state under the
   same history monitor.

**Successful Clear all:** the source still obtains \`r401FileGate\`,
waits for prior writes, deletes the actual file with
\`historyStore.clearWithReceipt()\`, clears pending/current panel rows
and marks a clean state. Newly arriving drops can now admit autosaves.

**Failed Clear all:** the prior disk bytes and panel are intentionally
retained, \`r401ClearUnsafe=true\` quarantines automatic writes, and the
user can attempt another explicit Clear all. An old worker may not
automatically rewrite history after a failed clear. This is fail-closed
rather than a complete non-destructive recovery UI.

**Not changed:** per-source/per-type/record confirmed deletion receipt
behavior, the R401 FileGate, the R403 one-worker executor model, the R404
atomic item DTO snapshot, the R405 deep panel snapshots, final shutdown
save, logout save, and existing EDT sync I/O.

## Verification on owner Windows

- Private **JDK21 \`javac --release 11\`** full-source build passed:
  **1,277 Java sources → 1,388 class files**, exit 0.
- Byte comparison vs exact R405 private candidate:
  **one changed Java source and one changed class**, both
  \`LootTrackerPlugin\`. Full class tree unchanged otherwise. Compared
  with independently SHA-pinned R381 corpus, differences remain
  confined to the previously known five private Loot Tracker Java
  sources and seven associated classes.
- The public read-only SHA-pinned
  \`tools/r407/audit_clear_autosave_epoch.py\` was executed against
  the actual private original, prior and current owner-source/class
  trees. Its receipt:
  **\`R407_PRIVATE_CLEAR_AUTOSAVE_EPOCH_GATE_PASS\`**, exit 0.
  It verifies exact scope, lock placement, epoch ordering, guarded
  worker receipt reset, guarded exception retry, prior writer fences,
  synchronous confirmed deletion and shutdown semantics.
- Synthetic public verification locally:
  **37/37 Python** source/class negative/positive tests PASS and
  **22/22 Java** invented interleaving tests PASS. The Java suite was
  repeated **5/5** times without failure. Scenarios cover a queued
  worker, worker holding the file monitor during clear, successful
  deletion, failure quarantine, repeated clears, explicit retry,
  newly arrived drops, stale exceptions and stale post-clear worker
  completion.
- Owner TEMP-only custody archive
  \`R407-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\` SHA256
  \`e1b28ea9c912a8a640c5889e511bd6fcc64edb9db35093658ec5d404cce7a7be\`.
  It was compiled and packaged but **never launched, installed,
  uploaded, distributed or executed**.

## Important remaining limitations

The source-level fix is not actual plugin runtime acceptance or proof
of all possible schedules. The synthetic model uses invented data and
a small in-memory fake writer; it cannot establish original-client
Swing timing or true crash persistence.

Confirmed deletion and Clear all still execute synchronous disk I/O
on the EDT, and may first block behind the background writer's
file-operation lock. The original client hang's root cause remains
unproved; the R406 contention analysis was an observable risk, not a
verified explanation of that hang.

R407 does **not** establish cross-process writer locking, lossless
power failure, complete serialization across every possible mutation,
an integrated durable event journal, v309 original parity, or live
v312 compatibility. In particular, an asynchronous deletion with
durable success/failure UI is still a separate R408+ architectural
problem.

No independently verified restricted test guest with network egress
blocked and production mounts read-only is available. No original
private game-client process, real player data, friend packages or
\`C:\Users\Felix\Desktop\fullspkclient\` was touched.

**Keep draft/unmerged; no original/private source release, client
launch, production rollout, merge or distribution is authorized.**
