# R404 — atomic per-item DTO snapshot during background loot-history saves

**Repository:** Trexzo/SpawnPK-Client.
**Stacked on:** R403 draft PR #1199.
**Status:** DRAFT / UNMERGED. Owner-private source release and runtime execution gates remain CLOSED.

## Narrow problem confirmed in private source

R403 moved normal saves to a single daemon background worker, but the existing
\`LootHistoryStore.RecordDto.from\` and \`ItemDto.from\` serializer still
traversed **live mutable loot records and items**.

The Swing EDT can change a loot item's \`name\`, \`price\` and
\`ignored\` flag independently while the worker is serializing it.
For example, definition refresh formerly called \`setName(...)\` and
later \`setPrice(...)\`. The serializer could read a **new name and old
price**, or the reverse. The record's array reference was also fetched
multiple times, rather than once per record.

A global monitor around the entire history, Swing repainting and
disk commit would create more EDT stall/deadlock risk. R404 instead
establishes a small, local per-item serialization boundary.

## Owner-private R404 candidate: exactly three source edits

The isolated owner TEMP candidate copies R403 and modifies only:

- \`rs/plugins/loottracker/LootTrackerItem.java\`
  - Name, price and ignored-flag setters now synchronize on the item.
  - A new synchronized \`r404ApplyDefinition\` updates name and price
    **in one item-monitor interval**.
  - The prior policy is retained: an absent definition name leaves
    the existing name unchanged, and the price replacement still
    applies when \`newPrice > 0 || existingPrice <= 0\`.
- \`rs/plugins/loottracker/LootHistoryStore.java\`
  - Record-to-DTO conversion reads and clones the item-reference array
    **once** before iterating it.
  - Item-to-DTO conversion synchronizes on that item while copying its
    ID, name, quantity, price and ignored flag into a **new independent
    DTO**. The subsequent JSON write uses DTOs rather than reading
    the live item again.
  - Null entries fail closed rather than silently substituting data.
- \`rs/plugins/loottracker/LootTrackerPlugin.java\`
  - The definition-refresh Swing callback now computes its candidate
    name and price, then calls \`r404ApplyDefinition(...)\` once per
    item, preserving its existing \`requestSave()\` follow-up.

This avoids introducing nested history/file gates during item
mutation. It does **not** lock the entire panel for all price refreshes,
nor guarantee a single atomic snapshot across every record or item.
A background save can still capture some items from before a bulk
repricing and others from afterward. The subsequent dirty-save request
can eventually correct that state if the process continues.

## Verified owner-local Windows evidence

- Full Windows JDK21 \`javac --release 11\`: **1,277 Java sources
  compiled to 1,388 class files**, exit 0.
- Full source-byte comparison with R403: **exactly three changed files**
  listed above. Full class-byte comparison: **exactly four changes**:
  \`LootTrackerItem.class\`, \`LootTrackerPlugin.class\`,
  \`LootHistoryStore$ItemDto.class\`, and
  \`LootHistoryStore$RecordDto.class\`.
  The enclosing \`LootHistoryStore.class\` did not change compared to
  R403; compared with pinned R381 the source and class differences
  remain restricted to the four historical Loot Tracker sources and
  six corresponding compiled classes.
- The inherited compile script included a hardcoded prior-stage
  \`changed_private_sources=1\` metadata count. An independent
  **\`R404_PRIVATE_COMPILE_SCOPE_RECONCILED_PASS\`** receipt re-counted
  the actual byte changes (three Java sources, four class files)
  without modifying private source or rewriting the compiled output.
- SHA-pinned read-only \`tools/r404/audit_atomic_item_snapshot.py\`
  run against the actual isolated private source and compiled classes:
  **\`R404_PRIVATE_ITEM_SNAPSHOT_STATIC_GATE_PASS\`**, exit 0.
- **33/33** public Python synthetic positive/negative source/byte
  gate tests and **18/18** standalone Java item-snapshot scenarios
  passed locally. The Java model includes a two-thread item-monitor
  test, 5,000 concurrent definition-update iterations, deliberately
  torn legacy snapshots, and explicit coverage of cross-item
  inconsistency as a remaining limitation. These tests use only
  fabricated records.
- Owner-TEMP custody archive only:
  \`R404-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`,
  SHA256
  \`7701e7ea8349a78eb56bb81c30cc56d3751b2d19328252672574f758a02531db\`.
  Packaged but **never launched, installed, uploaded, distributed,
  or executed**.

## Important remaining limitations

This does **not** eliminate the remaining EDT freeze risk: the R401
file gate may still be held by a background writer when the EDT
requests a confirmed deletion. Logout, shutdown and per-row deletion
also deliberately retain synchronous file-I/O receipts. Eliminating
that remaining latency requires a separately validated **asynchronous
edit admission and durable acknowledgement** design.

This is not an atomic whole-history transaction. Bulk repricing,
ignored-item changes, aggregates and other UI mutations still need a
cross-record snapshot/edit version protocol; per-item coherence does
not establish a globally consistent point in time. There are still
old callbacks to audit across plugin restarts.

No original private client runtime acceptance, actual Swing
scheduling benchmark, v309 original equivalence, v312 compatibility,
cross-process file locking, crash recovery, power-loss guarantees or
confirmed startup-freeze root cause. The R397 journal remains a
separate synthetic prototype, not integrated into the candidate.
There is no independently verified restricted guest with blocked
external egress and read-only production mounts.

**Keep draft/unmerged. Do not launch the private game client on the
normal host, publish recovered code, merge or distribute this candidate.**
