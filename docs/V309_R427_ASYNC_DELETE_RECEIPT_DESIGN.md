# R427 — EDT-safe, asynchronous history deletion receipts (public-only prototype)

**Repository:** Trexzo/SpawnPK-Client  
**Stacked on:** R426 draft PR #1222  
**Status:** DRAFT / UNMERGED / NOT DEPLOYED. No private Java source or production cache modified.

## Motivation

The existing Loot Tracker private implementation still has synchronous confirmed-deletion and Clear all paths that may perform history disk I/O on Swing's Event Dispatch Thread (EDT). That can block painting/input and contribute to apparent UI freezes. Prior R401–R426 work hardened concurrent save/clear ordering, history deletion journals, owner leases, directory safety and source-pinned build verification; it **did not** make these confirmed-delete UI actions asynchronous. We must not assume that simply creating a background thread solves durable deletion, stale UI callbacks or restart races.

Desktop Commander remains quota-paused, so R427 is an independent, **public-only Java 11 proof-of-design**, not a change to the owner-private `LootHistoryStore.java` or `LootTrackerPlugin.java`.

## Implemented prototype

`tests/fixtures/r427/R427AsyncDeleteCoordinator.java`

The coordinator defines a narrow integration contract rather than including private recovered code:

- `Request` captures a durable **kind** (`CLEAR_ALL`, `RECORD_IDS`, `SOURCE_KEY`, `TYPE_KEY`), immutable stable identifier values (not Swing row indices), original UI version and monotonically increasing session epoch **on the EDT**. It refuses malformed, ambiguous or unbounded (>4,096 keys) requests.
- **Exactly one** request may be in flight. A dedicated single managed **non-daemon I/O worker**, not the EDT, executes the synchronous `Store.commit()` adapter. No busy-spin, repeated executor creation, polling, timeout retry or optimistic UI delete.
- `Store.commit(request, admission)` must own the R419 OS writer lease, check the R411 journal state, hold the proper history/session gate at the *durable commit boundary*, and return `CONFIRMED` only once the complete disk transaction and receipt are durably committed. `admission` must be rechecked under that store gate. **The coordinator does not implement file format, deletion intents, acknowledgment, fsync or the private store adapter.**
- `REFUSED` means a definitive noncommit; the existing panel remains unchanged. `UNCERTAIN` or an exception after a possible write leaves the panel unchanged, quarantines further deletion attempts in this coordinator, and requires an independent reconciliation path; it **must never auto-retry**. A private integration must persist quarantine state through restarts and respect R415–R417 evidence.
- A `CONFIRMED` receipt reaches Swing with `invokeLater`. The panel is changed only if the original session is still active and its version is still the same. A version mismatch triggers `confirmedButNeedsReload` instead of deleting possibly unrelated rows. This callback must schedule a nonblocking restore, not perform disk I/O on EDT.
- On `closeAsync()`, incoming requests are immediately rejected. The same serialized I/O worker **drains any already accepted durable operation before calling `Store.closeOwner()`**; Swing's EDT never joins it or releases the lock. Results from an invalidated/closed session are never applied to the UI. The caller must coordinate the plugin's existing final shutdown-save transaction with this ownership queue; otherwise a second release path could race. **The worker is intentionally non-daemon:** an accepted durable operation is not silently abandoned on an ordinary JVM exit, but a blocked filesystem operation can delay process termination. An owner-private integration must provide a clearly bounded shutdown and failure escalation contract without blocking Swing's EDT.
- The package-private `Session`, `Store`, and `View` interfaces are intentionally narrow so an owner-private adapter can be code-reviewed independently. They are **not** substitutes for R419/R415 writer-admission, journal safety or synchronized disk/lock operations.

## Public acceptance

`tests/fixtures/r427/R427AsyncDeleteHarness.java` executes **real Swing EDT callbacks** and a separate worker against an independently authored fake durable store. It verifies 15 behavior scenarios:

1. Confirmed receipt arrives only after worker durability and is applied on EDT, never optimistically.
2. Stable IDs are copied, deduplicated and immutable.
3. A concurrent second request is refused while one is in flight.
4. Refused disk result does not delete UI rows.
5. Uncertain result blocks blind retry.
6. Simulated post-durable-write exception is treated as uncertain/quarantined.
7. UI version changes require refresh, not stale row removal.
8. Stale session callbacks cannot mutate a new panel.
9. Session invalidation before admission refuses the request.
10. Shutdown while a commit is held drains that commit before owner release, without blocking EDT.
11. No-request shutdown is idempotent.
12. Non-EDT request/close calls are refused.
13. Invalid intent shapes/keys are refused before queuing.
14. A real Swing input callback runs while an accepted disk worker is deliberately blocked, demonstrating EDT responsiveness without an optimistic deletion.
15. A **fabricated file** is written and `FileChannel.force(true)` called on the worker before a confirmed UI receipt; no real player file is opened.

`tests/test_v309_r427_async_receipts.py` compiles the coordinator/harness with **`javac --release 11`** and runs the scenarios as isolated JVM subprocesses under fresh direct `R427-Synthetic-*` TEMP directories. Seven additional static safety checks confirm code/import and scheduling boundaries. Hosted matrix: Windows/Ubuntu × Python 3.11/3.13 + JDK21.

Passing these tests only proves the **public synthetic prototype**'s behavior. It cannot prove the recovered private store's durability, journal ordering or live-game FPS improvements.

## Hard integration blockers

1. **No private-source modification in R427.** Desktop Commander is online but service tool calls remain paused due to monthly usage limits. No alternative route or reconnection is attempted.
2. The current actual `LootHistoryStore.clearWithReceipt()`, deletion journal and group/record delete semantics have to be inspected and mapped to `Store.commit`. No unsafe substitute or copy of private bytecode is published.
3. The store must actually return `CONFIRMED` only after durable acknowledgment/receipt under R419 owner lease, and must refuse unsafe journal/epoch states atomically at its commit boundary. A single in-memory `BooleanSupplier` check alone is not a security or correctness fence.
4. `r395HistoryGeneration`, `r399AcceptingDrops`, plugin instance identity and all panel-edit paths must feed a **complete** UI version/epoch fence. Prior R400 version increments may not cover row/source/group deletion paths. A mismatched UI should schedule a nonblocking re-read.
5. Shutdown must not race an existing `r419ShutdownCommitThread` or close the lease before a final-save task. One serialized owner-writer queue (or shared receipt gate) and an accepted close/drain order are needed.
6. Ambiguous post-write exceptions require a **persisted** quarantine and forensic recovery policy before restart; in-memory `quarantined` is insufficient for deployment.
7. The R422 actual-private multiprocess retest, R425/R426 actual-private compilation/overlay acceptance, full LootTrackerPlugin EDT lifecycle and v312 runtime testing remain outstanding. No automatic legacy cleanup, marker reconciliation, merge or release is authorized.

**Next private phase:** Once authorized owner-PC access resumes, integrate an opt-in no-auto-deletion controller in the isolated source, adapt only one confirmed-clear path first, verify the true disk receipt/journal contract and shutdown order, compile full Java sources, exact class delta, and exercise the real plugin's EDT acceptance before expanding to record/source/type deletions.

**Release gate remains CLOSED.**
