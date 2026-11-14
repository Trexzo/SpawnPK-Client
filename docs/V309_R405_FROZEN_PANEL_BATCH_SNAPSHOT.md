# R405 — frozen panel and pending-record snapshot before history serialization

**Repository:** Trexzo/SpawnPK-Client.
**Stacked on:** R404 draft PR #1200.
**Status:** DRAFT, UNMERGED, PRIVATE SOURCE AND RUNTIME RELEASE CLOSED.

## R404 limitation confirmed in source

R404 prevented tearing **inside one item's** mutable name/price/ignored
fields. It did not provide a consistent snapshot across the entire
canonical panel record list. The background worker could copy item A
before a bulk repricing, then item B afterward. Similarly, a bulk
ignored-list update could change several entries while the background
store traversed them.

R405 restricts this boundary without acquiring the history or file
monitor while reading Swing panel state and without using
\`SwingUtilities.invokeAndWait\`.

## Owner-private R405 candidate

The isolated candidate was cloned from R404 on the authorized owner
Windows PC; changes are restricted to four private Java sources:

- \`rs/plugins/loottracker/LootTrackerItem.java\`:
  \`r405FrozenCopy()\` creates a new item containing the ID, name,
  quantity, price and ignored flag while holding the R404 item monitor.
- \`rs/plugins/loottracker/LootTrackerRecord.java\`:
  \`r405FrozenCopy()\` creates a new record with a copied array of
  copied items, preserving original title, subtitle, type, **raw kill
  count** and timestamp. Missing item entries fail closed.
- \`rs/plugins/loottracker/LootTrackerPanel.java\`:
  \`r405FrozenRecords()\` freezes **all canonical panel records under
  the panel monitor**; it returns detached objects, not the original
  Swing-backed items. Existing \`getRecordsOffEdt()\` remains
  available for its other read-only callers.
- \`rs/plugins/loottracker/LootTrackerPlugin.java\`:
  - The price-definition refresh callback now holds the **same panel
    monitor** while updating all available panel records and derived
    aggregates; the repaint/rebuild and save request remain outside
    that monitor.
  - \`persistHistory()\` uses \`panel.r405FrozenRecords()\` for its
    ordinary panel portion instead of taking a shallow reference list.
  - The pending queue's object identities are still tracked for
    successful-save acknowledgment; however, the *values* written for
    pending records are now independent deep copies. A **second**
    handoff-version / clear-generation check after cloning pending
    records rejects captures that raced a pending-to-panel transfer.

The existing panel's \`updateIgnoredRecords()\` already updates all
canonical rows while holding its own monitor. Hence both identified
**bulk** value mutators now use the snapshot monitor.

All deep copies happen **before** entering the R401 file-operation
monitor, so the JSON writer sees stable item/record objects even if the
original UI values later change. The same epoch and no-data-loss
receipt checks from R400–R404 are retained. Deep copying does *not*
make the original source's per-instance file monitor safe for
cross-process concurrent writers.

## Local evidence from authorized owner Windows

- JDK21 \`javac --release 11\` compiled **1,277 Java sources into
  1,388 class files**, exit 0.
- Exhaustive SHA/byte comparison with private R404: **four changed
  Java sources and exactly four corresponding compiled classes**:
  \`LootTrackerItem.class\`, \`LootTrackerRecord.class\`,
  \`LootTrackerPanel.class\`, \`LootTrackerPlugin.class\`.
  Against the pinned original R381 corpus, exactly five Loot Tracker
  sources and seven relevant compiled classes differ.
- The SHA-pinned read-only static gate on the actual owner-private
  source/class trees returned:
  \`R405_PRIVATE_FROZEN_PANEL_STATIC_GATE_PASS\`, exit 0.
  The gate verifies the exact original, previous and candidate
  source/class scopes, panel-monitor ownership, frozen item/record
  copy semantics, price/ignored batch guards, pending handoff recheck,
  and that no Swing wait or disk monitor was added to panel freezing.
- Public-only invented synthetic tests on Windows:
  **34/34 Python** source/class acceptance and negative controls and
  **19/19 Java** deterministic snapshot/concurrent batch/handoff
  scenarios passed. Tests contain no reconstructed source and no
  real player data.
- Private custody-only compiled JAR under the owner TEMP workspace:
  \`R405-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`
  SHA256 \`d8500fffc2eabba7691c0f5b8bd58052e01f259f7d02394c349b946fe8a9cf32\`.
  **Never run, installed, uploaded, distributed or shared.**

## What remains unresolved

This is a **consistent snapshot of the canonical panel during the
two identified bulk mutations**, not a formal serializable transaction
across all application state. A menu action toggling a single
individual item, live-drop callbacks outside the panel list, session
transition, and changes after freezing but before acknowledgment
still require separate version checks and runtime validation.
The pending/handoff generation safeguards are limited to known
producers. Price refreshes that arrive after snapshot completion
require the subsequent normal save to persist new values.

Deep copying a very large panel holds its monitor for the duration
of the memory copy; this can delay an EDT edit. **No measured UI frame
or disk latency** was obtained in an actual game runtime.

The R401/R402 file monitor still allows an active background writer
to block a confirmed EDT deletion, and confirmed deletion, clear all,
logout and shutdown still perform synchronous disk operations.
R405 does **not** make them nonblocking. For R406, prioritize a
read-only contention/latency investigation and a separately proved
asynchronous acknowledgment protocol before changing their behavior.

No full original client run, isolated guest runtime, original v309
equivalence, live v312 compatibility, cross-process history locking,
crash recovery, power-loss durability or confirmed root cause of
the reported startup freeze. The R397 journal remains independent
research and is not integrated.

No production client, real history files, accounts, friends'
distribution packages or normal-host sessions were modified.
**Keep draft and unmerged; no private launch, merge or release authorized.**
