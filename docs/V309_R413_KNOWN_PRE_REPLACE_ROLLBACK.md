# R413 — rollback only for proven pre-replacement confirmed-deletion failures

**Repository:** Trexzo/SpawnPK-Client  
**Stack:** directly on R412 draft PR #1208  
**Status:** DRAFT / UNMERGED. Private source/runtime release gate CLOSED.

## R412 finding and safe scope of R413

R412 added a metadata-only staging-file admission check inside the
confirmed deletion's \`r401FileGate\`, **before** the Swing panel is
mutated. R411 also checks for unresolved
\`loot-history.json.tmp\` at the writer boundary. But a different
process can create the staging path *between* these two checks, or
the local history writer may fail during serialization or forcing
the temporary file. In those cases, the existing UI deletion
can complete even though **no replacing history write was
attempted**. R412 then marks the history unsafe, but the panel
is left missing the confirmed record.

This R413 experiment restores the panel's precise original row
identities when—and **only when**—the writer can establish that
its atomic history replacement was never attempted. This
is not a journal implementation, power-loss repair or a
general rollback guarantee.

## Owner-private R413 source changes (not committed here)

Fresh owner-TEMP copy of R412, limited to exactly three classes'
source files under \`rs/plugins/loottracker\`:

### 1. \`LootHistoryStore.java\`

A new nested writer disposition enum and a per-save state:

- \`NOT_ATTEMPTED\`: the confirmed edit reset the disposition,
  but its persist routine did not call \`saveWithReceipt\`.
  **No automatic UI rollback**, because no authoritative
  success/failure receipt exists for this operation.
- \`FAILED_BEFORE_REPLACE\`: the writer entered
  \`saveWithReceipt\`, but refused due to staging, invalid
  inputs, failed staging creation, serialization or force
  **before** attempting an atomic move. **Only this state**
  authorizes rollback to the old panel identity snapshot.
- \`REPLACE_ATTEMPTED\`: the strict atomic-move call is
  about to execute or may have executed and raised an
  error. A non-success result here cannot prove which
  history image was committed. **Do not roll back.**
- \`COMMITTED\`: the history's strict move returned success.
  Retain the confirmed panel deletion and the existing
  success receipt.

The disposition starts as \`NOT_ATTEMPTED\` at the
beginning of each confirmed deletion under its local
FileGate. Each \`saveWithReceipt\` first marks
\`FAILED_BEFORE_REPLACE\`. The state advances to
\`REPLACE_ATTEMPTED\` **before** calling R410's
\`AtomicFileReplace.moveStrict\`, and to \`COMMITTED\`
only if that call returns normally. An exception after
entering the replacement step never restores the
\`FAILED_BEFORE_REPLACE\` state.

No history format/schema change, orphan recovery, stage
payload reading, automatic temp deletion or new disk file
is introduced. Existing R410 \`CREATE_NEW\`,
buffer flush, channel force and strict atomic replacement
remain. Ordinary autosave, confirmed deletions and Clear all
still share the existing local \`r401FileGate\` for write
serialization.

### 2. \`LootTrackerPanel.java\`

A new nested \`R413DeleteSnapshot\` captures, on the
Swing EDT and under the panel's monitor:

- The canonical list of **original record object identities**
  in original order. Records with identical source/type are
  not confused with one another; snapshots intentionally
  use a shallow copy of the list, not new record objects.
- The source filter title/type and currently selected page.
- The overall/grouped view flags.

When the plugin proves its write failed **before**
replacement, \`r413RestoreDeleteSnapshot\` replaces
the canonical panel list with those same record objects,
restores navigation flags, recounts derived aggregates,
restores the filter chrome and rebuilds the visible rows.
The restoration runs synchronously on EDT without a disk
write or blocking cross-thread Swing hop.

Because the deletion transaction already occupies EDT,
no other normal Swing callback should modify the panel
between the snapshot and synchronous restoration. **This
assumption is not a verified all-thread-schedule guarantee**.
The snapshot also does not freeze all mutable record fields,
and a foreign producer may still modify disk history
outside the local monitor.

### 3. \`LootTrackerPlugin.java\`

\`r402ApplyPanelDeletion(Runnable)\` retains the R412
preflight, original loaded/unsafe/handoff/session guards,
UI-only behavior and synchronized acknowledged save.
For persistent confirmed edits it now:

1. Captures panel identity/navigation state after passing
   stage preflight and **before** running the edit mutation.
2. Resets the store writer disposition before invoking
   the existing mutation and synchronous \`persistHistory()\`.
3. On unacknowledged disk commit, retains
   \`r401ClearUnsafe=true\` and refuses automatic rewrites.
4. Restores the captured panel snapshot only when the
   store disposition is exactly \`FAILED_BEFORE_REPLACE\`.
5. Keeps the edit transaction-open flag set **until**
   any rollback finishes. The existing \`finally\`
   still releases it even if restoration throws.

An ambiguous after-move exception deliberately leaves the
UI un-restored and history quarantined rather than
possibly reinstating rows already removed from disk.

## Owner-private verification

- Fresh isolated copy, not the user's live v312 Desktop client.
- Windows JDK21 \`javac --release 11\`: **1,277 Java
  sources → 1,391 compiled classes PASS**.
- Exhaustive source/class byte comparison against R412:
  **exactly three changed Java sources**, their
  **three existing compiled classes changed**, and
  **two new nested classes**:
  \`LootHistoryStore$R413WriteDisposition.class\` and
  \`LootTrackerPanel$R413DeleteSnapshot.class\`.
  Every other original source and compiled class matches
  R412 byte-for-byte; no original R381 source/class drift.
- SHA-pinned public-only read-only audit
  \`tools/r413/audit_known_precommit_rollback.py\`
  against the actual isolated owner-private source/class
  trees: **\`R413_PRIVATE_KNOWN_PRE_REPLACE_ROLLBACK_GATE_PASS\`**,
  exit 0. It enforces writer phase ordering, exact-only
  rollback predicate, restoration before transaction
  closure, no old autosave/startup-method changes, source/
  class byte scope and no accidental cache/mover change.
- **37/37 Python** fabricated positive/negative tests
  PASS locally. Tests caught and prompted repairs to two
  verifier gaps: an inverted rollback predicate and
  premature closure of the deletion transaction.
- JDK21 standalone synthetic invented filesystem model:
  **22/22 Java cases PASS**, repeated **5/5** times.
  Tests cover an orphan appearing after preflight,
  a failed stage write, identity preservation with
  equal-title records, filter/page restoration,
  group/type/one-row deletions, persistent unsafe
  quarantine, unsupported strict move,
  a real atomic rename followed by a fabricated error,
  no-write-attempt ambiguity and local FileGate
  scheduling.
- Private owner TEMP custody-only archive
  \`R413-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`,
  SHA256
  \`75f6ebcc5519bc4bb49e2421285bc734b7e6d448d70eda7246f89b4997606e71\`.
  It was compiled and packaged **but not launched,
  installed, uploaded, shared or distributed**.

## Important limitations

**Not a general failed-write rollback.** If the history
replacement was *attempted*, an error may arrive after
the destination bytes have changed. Restoring the old
panel in that situation would risk resurrecting a
deleted record on a later write. R413 therefore leaves
the panel and disk potentially divergent, with automatic
rewrites quarantined until proper reconciliation.

**NOT_ATTEMPTED is also not rollback-safe.**
An earlier rejection in \`persistHistory\` may prevent
entering the store. Without an operation-specific
commit/receipt journal, this state is treated
conservatively as unacknowledged and unsafe.

**Cross-process changes are not resolved.** Even in the
\`FAILED_BEFORE_REPLACE\` state, the local writer's own
rename was never attempted; another process may have
modified the same canonical history file. The panel
restoration is an in-session usability fix, not proof
of disk/UI parity against arbitrary foreign writers.

**No EDT latency improvement.** The confirmed edit still
holds \`r401FileGate\` and synchronously performs a
JSON write; a rollback can require another Swing
rebuild on the same event thread. Any latency trade-off
must be measured in a verified restricted guest before
a release decision.

**No power-loss durability guarantee.** Directory
metadata forcing, cross-process lock ownership,
authenticated before/after commit journal,
staging-image reconciliation and safe cleanup
remain unimplemented. Source and synthetic tests
are not original-client behavior proof. No v312
compatibility, game startup acceptance, runtime
UI benchmark or original freeze root cause is proven.

The public PR contains no original/recovered private Java
source, compiled client class, JAR, loot history, staging
payload or credential.

## R414 suggested next

Develop and verify a **bounded transaction journal / restart
reconciliation** around the R410 strict writer and R413
writer-disposition boundary. It must distinguish a
definitely uncommitted image from a committed-but-
unacknowledged image after restart, reject interprocess
conflicts and restore the UI from a verified disk image
before any ordinary autosave can overwrite it. That
must be established before replacing synchronous
confirmed edits with asynchronous operations.

**Keep R413 draft and unmerged. All private-client
launch, installation, merge and distribution gates
remain CLOSED.**
