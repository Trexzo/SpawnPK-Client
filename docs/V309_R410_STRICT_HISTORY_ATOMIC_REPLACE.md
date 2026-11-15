# R410 — strict atomic history replacement and staged-file forcing

**Repository:** Trexzo/SpawnPK-Client.  
**Stack:** directly on R409 draft PR #1205.  
**Status:** DRAFT / UNMERGED, owner-private runtime and release gates CLOSED.  
**Scope:** isolated two-source private experimental build, public-only synthetic verification and read-only static gates.

## R409 finding and narrow R410 repair

R409 demonstrated a file-backed synthetic mechanism for restarting after
a history deletion committed on disk but before its EDT success callback
ran. The private client's *current* writer did not meet that prototype's
write assumptions:

- \`AtomicFileReplace.move(...)\` first attempted
  \`ATOMIC_MOVE\` but fell back to a **non-atomic**
  \`REPLACE_EXISTING\` when the atomic move was unsupported.
- \`LootHistoryStore.saveWithReceipt(...)\` serialized
  \`loot-history.json.tmp\` through a buffered output stream without
  an explicit staged-file \`FileChannel.force(true)\`.
- The existing temporary filename was reused with default stream
  creation behavior; an unresolved earlier staging file could be
  overwritten before its recovery status was assessed.
- The shared move helper was also called by
  \`TradingPostPrices.java\`, so disabling the fallback globally
  could unexpectedly break the price-cache writer.

R410 limits its private experimental change to:

1. **\`AtomicFileReplace.java\`:** adds a history-only
   \`moveStrict(temp,target)\` operation. It requires both files'
   canonical parent directories to match and attempts a replacing
   \`ATOMIC_MOVE\`. An \`AtomicMoveNotSupportedException\`
   propagates rather than falling back to a plain move.
   Transient \`FileSystemException\` retries retain the previous
   five attempts/50 ms policy; interruption restores the thread's
   interrupted bit and refuses to claim a successful replacement.
   **The existing \`move()\` method is unchanged** and remains used
   by the price-cache writer.
2. **\`LootHistoryStore.java\`:** opens the staged history file with
   \`FileChannel.open(..., CREATE_NEW, WRITE)\`. The existing
   JSON document is serialized through a buffered writer bound to
   that channel. After \`writer.flush()\`, it calls
   \`channel.force(true)\` before attempting
   \`AtomicFileReplace.moveStrict(...)\`.
   A preexisting unexplained \`.tmp\` file is **not silently
   truncated or deleted**. Refusal returns the existing false
   write receipt and retains prior main-file bytes where the
   replacement has not happened.

**Not changed:** JSON history schema/version, reader, clear-all
storage method, R407 session and autosave behavior, R405 frozen
snapshot semantics, R402 confirmed deletion path, R403 executor,
and the price-cache legacy move policy.

## Owner-private verification

- A new isolated owner TEMP source copy of R407 was used, not the
  live user's Desktop installation.
- Windows JDK21 \`javac --release 11\` **PASS**:
  **1,277 Java sources → 1,388 compiled class files**.
- Exhaustive source-and-compiled-class byte comparison against
  unchanged R407: **exactly two source changes and two class
  changes**, limited to \`AtomicFileReplace\` and
  \`LootHistoryStore\`.
  Against the independently pinned R381 compiled corpus, the
  difference is confined to **eight** Loot Tracker classes
  (the previous seven plus the move helper).
- The public-only read-only verifier
  \`tools/r410/audit_strict_history_atomic_replace.py\` inspected
  the actual owner-private prior/candidate sources and compiled
  classes, with SHA-pinned R381 source/archive references:
  **\`R410_PRIVATE_STRICT_HISTORY_ATOMIC_GATE_PASS\`**,
  exit 0. It verifies strict-move structure, exact source/class
  scopes, unchanged price cache, unchanged legacy mover,
  precommit flush/force ordering and absence of silent stage
  truncation/cleanup.
- Public synthetic local Windows acceptance:
  **36/36 Python** structural/corpus/negative controls PASS,
  **20/20 standalone Java 11-compatible real-TEMP-filesystem**
  scenarios PASS, with **5/5** subsequent Java reruns.
  The synthetic model exercises supported atomic replacement,
  unsupported atomic move refusal, retry exhaustion, interrupted
  retry, orphan stage preservation, old history preservation before
  replacement, fake postmove I/O ambiguity, and unchanged price
  cache fallback behavior.
- Private owner-TEMP custody archive only:
  \`R410-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`,
  SHA-256
  \`231ae26caee73ee59aeffc635fe08063f5a2a2c488e5eef61e0facf4e0738331\`.
  The archive was compiled and packaged but **never launched,
  installed, uploaded, distributed or executed**.

## Failure policy and important limitations

**The candidate is not crash-safe.** It forces the staged file before
renaming and demands an atomic replacing move, but does not
explicitly force the containing directory's metadata. On Windows
some directory-force strategies are not supported; the correct
policy cannot be inferred just from a successful return from
\`FileChannel.force(true)\` on a regular file. The system cannot
claim durability against sudden machine/storage-controller power
loss, or guarantee the order in which file and directory metadata
reach stable media.

**Postmove ambiguity remains:** an exception might be reported after
the target has changed. The existing boolean receipt cannot
distinguish "definitely not committed" from "committed but failed
to acknowledge." The R409 versioned sidecar intent/reconciliation
prototype remains **unintegrated**. This is an explicit blocker
for enabling asynchronous destructive actions.

**Orphan \`.tmp\` files deliberately stop saves** rather than being
deleted automatically. This is fail-closed and preserves recoverable
evidence, but can prevent routine autosaves after an interrupted or
locked history commit until deliberate reconciliation. R411 needs
a bounded, non-destructive inspection/recovery UI and automated
static tests for the new file policy. Do **not** solve this by
unconditionally deleting leftover temp files.

**EDT latency remains:** each confirmed source/type/row deletion,
Clear all, logout and shutdown still use synchronous disk I/O;
the 5-attempt move policy can include up to four retry delays.
R410 does not solve the original reported client freeze and may
change write latency and error frequency on filesystems that
lack atomic replacement.

**Other gaps:** no interprocess file lock, no integrated
post-commit/pre-EDT-ack journal, no actual game runtime acceptance,
no UI thread latency benchmark, no verified restricted guest,
no power-failure testing, no v309 equivalence or v312 compatibility.
The exact original freeze root cause remains unverified.
The public Java tests use fabricated files and an independent
model; they do not execute any recovered private Java class.

**Keep R410 draft and unmerged. Do not launch the private client,
ship the JAR, merge or install this experimental candidate.**
