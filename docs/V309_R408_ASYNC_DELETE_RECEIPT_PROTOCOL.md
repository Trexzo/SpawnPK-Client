# R408 — asynchronous confirmed-deletion receipt protocol, design-only acceptance

**Repo:** Trexzo/SpawnPK-Client  
**Stack:** directly on R407 draft PR #1203  
**Status:** DRAFT / UNMERGED. **No R408 private source edit, build, JAR, client launch, integration or deployment.** Public-only synthetic model, read-only baseline verifier, tests, CI and design notes.

## Source-confirmed problem and key architectural decision

The owner-private R407 code still invokes a confirmed deletion from the
Swing event-dispatch thread (EDT) and holds \`r401FileGate\` through the
panel mutation, synchronous \`persistHistory()\` and file-receipt
acknowledgment. The R403 autosave worker takes the same file gate;
therefore the EDT can wait for another writer **and** perform its own
file serialization and disk write.

The old helper cannot safely be changed to
\`executor.execute(mutation)\`: \`mutation\` calls Swing-specific
methods and must remain on EDT. A queued job is not an acknowledged
file commit, and snapshots taken before a confirmed deletion can
resurrect deleted records afterward.

The R408 proposal is a **three-stage transaction with a terminal
receipt** rather than "just do the same work on a background thread":

1. **EDT admission, no destructive mutation.** Capture exact
   selected **record object identities** (not source-name equality)
   from the visible panel. Validate history loaded, live session,
   current plugin identity and no other unresolved edit; refuse
   with useful UI feedback if invalid. Mark a unique operation as
   **PENDING**. Keep all panel rows visible, and do not claim deletion
   succeeded or write a new file merely because a job was queued.
   UI-only mode when persistence is disabled remains distinct.
2. **Serialized worker transaction.** One background executor
   serializes deletion and autosave requests with the existing
   \`r401FileGate\`. After locking, it validates the captured
   session/operation generation. Freeze the latest panel and pending
   records under their existing source monitors using a
   cross-collection handoff token; retain a parallel map from
   original object identity to frozen record to exclude only the
   confirmed targets. Preserve all other records and new live drops.
   No Swing mutation, repaint or blocking EDT hop occurs on the
   worker. An in-flight older autosave may complete **before** this
   deletion, but no older snapshot may commit afterward.
3. **Commit, then EDT acknowledgement.** Write a temporary complete
   record document and request an **actual success receipt after
   atomic replacement**. Post an EDT callback with the exact
   operation/epoch token. Only the current successful receipt may
   remove the previously selected **original object identities**,
   rebuild the panel, clear PENDING and display **SAVED**. A failed
   write keeps the UI records unchanged and reports failure. An
   ambiguous after-replace error must quarantine automatic writes:
   it is unsafe to claim either deletion or rollback succeeded.
   New drops received after the frozen snapshot get their own
   later autosave once the unresolved edit finishes.

Overlapping delete confirmations are **refused with visible feedback**
until the first commits, fails or is explicitly canceled. Coalescing
cannot silently turn multiple confirmed destructive actions into
one unknown operation.

## Concrete unintegrated synthetic model

\`tests/fixtures/r408/R408AsyncDeleteProtocolSynthetic.java\`
is original, invented, Java 11-compatible code. It implements a
single-thread daemon IO executor, in-memory panel/pending/disk
collections, original-object-identity selection, file monitor,
generation checks, queued EDT callback, terminal statuses
(PENDING, COMMITTED, FAILED, AMBIGUOUS, CANCELED, REJECTED),
blocking/admission of stale autosaves and fake disk receipts.

**23 deterministic synthetic scenarios** passed on owner Windows:
pending has no false success; disk commit has no early EDT
acknowledgment; equal-title records remain distinct; group
selection is restricted to confirmation-time identities; drop
arrivals while writing survive; pending-to-panel handoff remains
represented; before-replace failure preserves UI/disk; ambiguous
after-replace failure quarantines; busy operations are refused;
subsequent operations are accepted only after terminal
acknowledgment; stale autosaves cannot resurrect deleted rows;
Clear all and shutdown invalidate queued work; stale EDT callbacks
cannot alter a new session; no-match/UI-only paths are explicit.

The Java suite was additionally rerun **15/15** consecutive times.
The model has **no real filesystem**; its "disk" is a List, not a
durable file. It is evidence about the algorithm and guarded
interleavings only, **not a verified integration**.

## Additional release-blocking counterexample: commit before EDT ack

A worker can successfully atomically replace the disk document,
but a plugin stop/restart can invalidate the operation **before its
success callback runs on EDT**. Disk then reflects the deletion,
while the retained old panel still shows the row. A subsequent
ordinary save must not write that old row back.

The synthetic test deliberately reproduces this condition and
refuses to call it success. The model's \`staleAckCount\` captures
the unresolved state.

**R409 must resolve this before a production implementation:**
a versioned, restart-reconcilable completion receipt or durable
intent/commit journal (with an authenticated restoration path)
is needed, or an equivalent proven lifecycle barrier that does
not block the EDT indefinitely or allow a source-unverified
overwrite. A transient in-memory pending flag is insufficient.

There is a similar challenge if new live drops arrive after the
worker's frozen snapshot but before the commit: they remain on
screen and need a subsequent save, but a crash in that interval
can lose the unsaved new drops. The existing R403 pattern does not
guarantee durability of all concurrent arrivals.

R397's CRC journal is still a **separate synthetic research
prototype**, not integrated or proven suitable as-is. It must not
be treated as a completed answer to these issues.

## Actual owner Windows passive review

The new read-only tool
\`tools/r408/audit_async_delete_prerequisites.py\`
was executed against:

- Exactly SHA-pinned R381 recovered source and reference JAR.
- The **unchanged R407** owner-private source tree: **1,277 Java
  files**, and compiled tree: **1,388 class files**.
- Existing R381-vs-R407 scope restricted to the five Loot Tracker
  source files and seven matching class files already established.

The source audit returned
**\`R408_PRIVATE_ASYNC_EDIT_PREREQUISITES_PASS\`**, exit 0.
It verifies the three current delete selectors, identity-specific
single-record removal, current synchronous FileGate receipt,
Swing/UI callback ownership, R405 deep frozen data behavior,
R403 epoch-fenced autosaves, R407 Clear-all epoch reset, and
the history store's atomic replacement receipt. It also explicitly
reports **no integrated background deletion or restart-recovery
receipt**.

**35/35 Python** invented source/class negative tests passed locally,
including SHA pinning and no-overwrite receipt controls. Both audit
and synthetic model are portable to Windows/Ubuntu CI and publish
no private Java, class files, JARs, account information, histories
or original client code.

## Limits and next stage

No actual R408 private Java implementation was made, because
the post-commit/pre-ack lifecycle window is still unresolved.
In particular, blindly changing the R402 helper would introduce
an unverified possible history-resurrection bug, rather than
definitively eliminate the reported freezes.

For an R409 implementation candidate, require an explicit
lifecycle state machine and an independently validated
restart-reconciliation policy *before* moving confirmed mutations
to the worker. Then use an isolated private source copy, narrow
class-delta/full-source compile, public-only synthetic negatives,
read-only source and class audit and restricted guest runtime
acceptance before any merge or release discussion.

The current live v312 client, original game runtime, player data,
friends' packages and installed binaries were not executed,
modified or read. No real Swing latency, original startup freeze
root cause, v309 behavioral parity, v312 compatibility,
interprocess file serialization, power-loss durability or
authenticated recovery from ambiguous writes has been proven.
**This PR remains draft/unmerged; all private launch, merge and
distribution gates CLOSED.**
