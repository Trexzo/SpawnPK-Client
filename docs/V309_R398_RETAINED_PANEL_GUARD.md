# R398 — retained panel after failed persistence: private fail-closed guard

**Repository:** Trexzo/SpawnPK-Client. **Stacked on:** R397 draft PR #1193.
**DRAFT/UNMERGED; Source-M1 private source release gate CLOSED.**

## Newly documented failure case

The private reconstructed LootTracker panel can retain records after an unsuccessful
save when the plugin is disabled. Re-enabling the plugin previously allowed
the asynchronous restored disk history to append to that retained panel.
The system has no durable record identifier that proves whether a retained
row is already in the disk snapshot, and an equality check on title/type
cannot distinguish two genuine identical-looking drops.

There is no safe automatic merge of every possible retained panel state
without the durable event IDs/migration explored separately in the R397
journal experiment. In particular, blindly merging only the latest
pre-restore drop buffer risks silently dropping older uncommitted rows.

## R398 owner-private source candidate

The owner-local experimental candidate is under
\`R398-Private-Retained-Panel-Guard/Source-Candidate-R398\` in the existing
isolated TEMP root. It copies R397, changing ONLY
\`rs/plugins/loottracker/LootTrackerPlugin.java\`.

- On plugin startup, a previously **successfully committed** panel may be
  cleared before it is refilled from disk, as R397 intended. If no verified
  commit exists, the existing panel is snapshotted; any retained records
  set a volatile unresolved-provenance flag.
- If that flag is set, automatic history restore is **not started**, so
  old disk records cannot be silently appended to unverified panel rows.
- At pre-restore shutdown, the unresolved flag causes the strict disk
  merge to **refuse rewriting history** rather than relying on title/type
  equality or treating old panel contents as disposable. New drops in that
  session may remain volatile and are **not guaranteed durable**.
- Explicit user-triggered history clearing invalidates the flag.
- The R397 clean-stop fast path still requires the pre-restore drop
  buffer, pending callback queue, and panel snapshot all to be empty.
  The panel snapshot now occurs **outside** the \`r395HistoryGate\`
  monitor, avoiding the earlier nested \`historyGate → panel\` monitor
  acquisition; actual whole-program deadlock freedom is unproven.
- For new sessions with a genuinely empty panel, the R396 strict
  history-read, original-plus-live-drop merge and receipt-checked
  commit path remains available, with the same known dirty-shutdown
  EDT latency and disk error limitations.

This is a **conservative preservation change**, not a recovery mechanism.
It leaves ambiguous in-memory records visible while the process remains
alive, but cannot reconstruct them after abrupt process termination or
prove how to merge them with the existing file.

## Owner Windows static and compile verification

- Golden R381 source and reference JAR remain SHA-pinned as in R396/R397.
  The R398 changes were built only in an isolated private source copy.
- Windows JDK21 \`javac --release 11\` **1,277 sources → 1,388 classes**,
  exit 0. Direct bytewise class comparison showed **exactly one changed
  class vs R397**: \`rs/plugins/loottracker/LootTrackerPlugin.class\`.
  R381 still differs only in the two Loot Tracker classes established
  by R396.
- Public-safe read-only R398 verifier was run on the actual owner-private
  source and class trees. Status
  \`R398_PRIVATE_RETAINED_PANEL_STATIC_GATE_PASS\`, exit 0. It verifies
  exact one-source/one-class delta, retained-panel startup detection,
  pre-I/O restore/overwrite refusal, explicit-clear invalidation,
  three-buffer clean-stop guard, and panel snapshot outside the history
  monitor. Source structure is NOT runtime correctness proof.
- **18/18** public synthetic Python negative/positive gate tests
  passed locally; **14/14** standalone Java deterministic restart and
  concurrency-model tests passed, including failed-save reenable,
  identical-looking distinct drops, withheld auto-restore, explicit
  clearing, and a separate two-thread monitor ordering exercise.
- Private compiled artifact:
  \`R398-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`, SHA256
  \`1fc6f643d95bcd8b6e3253acc6224e45fed907f0ddeaf0c45d9d8866409daf30\`.
  Retained exclusively on owner Windows TEMP; not executed, installed,
  uploaded or released.

## Remaining blockers / next direction

The unresolved-panel guard intentionally prefers **not overwriting**
original persisted history, at the cost of leaving newer rows without
a guaranteed recovery route if the process exits. A correct migration
needs persistent per-drop IDs, an on-disk journal/snapshot watermark,
well-defined identity for historical v1 records, conservative duplicate
handling, a read-only preview of migration, and a tested rollback path.

The R397 journal remains a standalone public toy model. No journal
was integrated into the client. The dirty shutdown still performs
potentially expensive synchronous I/O, and queued drop callbacks from
old plugin generations warrant separate inspection before integration.

No real client/GUI/login/gameplay or production source was run or
modified. No guest with independently verified network egress denial
and no writable production mounts is established. Power-loss durability,
concurrent writers, original-v309 behavioral parity, live-v312
compatibility, and root cause of any observed frozen client remain
unproven.

**All launch/merge/release authorizations remain FALSE.**
