# R406 — passive EDT contention audit and discovered stale autosave admission

**Repository:** Trexzo/SpawnPK-Client
**Stacked on:** R405 draft PR #1201
**Scope:** public-safe analysis, synthetic concurrency reproduction, and read-only
source/class audit. **No private Java source changed for R406. No private JAR
was rebuilt. No client launched, deployed, installed, or distributed.**

## 1. Confirmed source-level EDT contention (not yet fixed)

The owner-private R405 plugin routes three confirmed panel actions through
\`r402ApplyPanelDeletion\`:

- \`LootTrackerPanel.removeSource\`
- \`LootTrackerPanel.removeType\`
- \`LootTrackerPanel.removeRecord\` (identity comparison \`r == record\`)

The method first requires the Swing EDT, then obtains the per-instance
\`r401FileGate\` monitor. **While holding that monitor on the EDT**, it
modifies the panel, calls \`persistHistory()\` synchronously, and reads
the write receipt before releasing the lock. The save routine also
obtains \`r401FileGate\`, then serializes all record DTOs, writes the
temporary history file and atomically replaces the destination.

R403's background routine autosave reaches \`persistHistory()\`
through its executor and therefore competes for **the same monitor**.
\`clearHistory()\` likewise runs on the EDT and obtains that file
monitor before its deletion receipt.

Two separate EDT latency mechanisms are therefore present:

1. **Lock contention:** an earlier autosave can already own the
   monitor when the user confirms a deletion or Clear all. The EDT
   cannot mutate or acknowledge until the writer releases it.
2. **Own synchronous disk write:** even without another writer, the
   confirmed deletion continues serializing and committing while
   the EDT runs inside the monitor.

Simply calling \`executor.execute(...)\` after the confirmation would
not preserve R402's success semantics: a job can be queued and later
discarded on shutdown, fail disk I/O, or race with another mutation.
A safe asynchronous edit needs explicit pending/committed/failed
states, epoch/generation checks, serial write admission and a way
to report failure without falsely acknowledging durable deletion.

## 2. Additional source-confirmed R403/R405 regression: Clear all
can strand routine autosaves

R405's \`clearHistory()\` increments \`r399SessionEpoch\` to invalidate
stale drop callbacks. It does **not** reset
\`r403AutosaveQueued\` or \`r403AutosaveDirty\`.

The R403 worker's \`finally\` block resets these flags **only if its
captured \`issuedEpoch\` still equals \`r399SessionEpoch\`**. An autosave
queued or running when Clear all advances the epoch can thus finish
with its cleanup suppressed. In the same plugin instance the
\`r403AutosaveQueued\` flag remains true, so later
\`r403QueueAutosave()\` requests coalesce into
\`r403AutosaveDirty\` instead of admitting a new worker. This could
continue until a plugin restart.

This is a conditional source-level race, **not a runtime-observed
incident**. The passive auditor requires the relevant session-epoch
increment, epoch-conditioned cleanup and missing clear-side flag
reset, and reports
\`source_confirmed_clear_can_orphan_r403_queued_autosave=true\`.
The issue is **NOT FIXED in R406**. It deserves priority over a
larger asynchronous deletion redesign.

A future narrowly scoped R407 candidate can make successful Clear
all retire and reset the old queue admission safely. It must not
allow an old worker to clear a new session's queue state, bypass
\`r401FileGate\` ordering, lose new drops, or misreport a failed delete.
A separate failure-path test is required because Clear all also
advances the epoch when its disk deletion fails.

## 3. Owner Windows evidence — completed

- R405 original private reference status:
  **R405 hosted workflow PASS, Recovery CI PASS**.
- The new public-safe passive tool
  \`tools/r406/audit_edt_file_gate_contention.py\` inspected the
  *actual* owner-private R405 source tree (**1,277 Java files**),
  matching compiled class tree (**1,388 class files**) and
  independently SHA-pinned R381 source archive/reference JAR.
  It verified that differences against original R381 remained
  restricted to the previously established **five Loot Tracker Java
  files and seven related compiled classes**.
- Read-only receipt in the owner's isolated TEMP acceptance workspace:
  \`R406_PRIVATE_EDT_CONTENTION_EVIDENCE_PASS\` is **not** the status;
  the exact current status is
  **\`R406_PASSIVE_EDT_CONTENTION_EVIDENCE_PASS\`**, exit 0.
  It records lock ownership, confirmed synchronous commit, queued
  epoch failure mode and explicit **release=false** flags without
  printing recovered Java or player history.
- Public synthetic verifier:
  **33/33 Python positive/negative tests PASS** on owner Windows.
- Standalone Java --release 11 model:
  **18/18 invented synthetic cases PASS**, run on JDK21. The same
  Java suite passed ten additional consecutive runs on Windows.
  Tests reproduce confirmed-EDT lock contention, Clear all waiting
  for autosave, UI waiting through its own synchronous write,
  missed/failed receipts, stale snapshots resurrecting a deleted
  record, per-instance-only lock scope, orphaned autosave flags
  following a clear, and a deliberately unsafe queued-but-not-
  committed deletion acknowledgement.

### Synthetic-only elapsed timing

An optional, informative \`--benchmark\` run introduced two
**artificial 75 ms** hold periods. On the owner Windows synthetic
model it observed:

- **75–77 ms** for simulated EDT waiting behind an autosave.
- **76 ms** for a simulated EDT's own synchronous write.

These numbers are artifacts of the injected delays, scheduler and
synthetic in-memory model; **they are NOT real client, disk,
graphics-frame, socket or game latency measurements**. Hosted
CI does not assert timing thresholds.

## 4. Next safe implementation steps

**R407** should first resolve and test the old queued-worker flag
following explicit Clear all. Must verify successful deletion, failed
deletion, worker already running, worker queued, new drop arrival,
worker restart and stale epoch cleanup independently. Follow with
a full private compile and scope audit; keep the client unexecuted
until an appropriate isolated acceptance environment is available.

After that, design an asynchronous confirmed-deletion protocol
with a proper durable acknowledgement and failure UI, or consider
an explicitly nonblocking refusal that does not silently consume
the user's confirmed action. Do not blindly change
\`r401FileGate\` to \`tryLock\` or move the existing Runnable to the
worker: both could break ordering or Swing-thread ownership.

## Release boundaries

R406 has **no new private source candidate** and **no private JAR**.
The unchanged R405 custody-only candidate remains in the owner's
isolated TEMP workspace; its previously documented hash still
applies. No normal-host private game launch, user history edit,
account access, friend package change, workflow merge, production
installation, distribution, original v309 equivalence, v312 runtime
compatibility, cross-process lock guarantee, crash/power-loss
durability, or verified root cause of the original freeze.

This PR is **draft and unmerged**, contains only synthetic code,
read-only diagnostics, docs and CI, and does not authorize release.
