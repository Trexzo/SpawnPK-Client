# R428 — bounded observation of asynchronous owner shutdown

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R427 draft PR #1223  
**State:** public synthetic design only; draft / unmerged / never deployed.

## Identified R427 gap

R427 moved a *hypothetical* confirmed-delete Store adapter to a single managed non-daemon I/O worker, with session/EDT fencing and ordered `closeAsync()` ownership release. It did **not** offer a bounded way for the UI to distinguish a normal shutdown from an indefinitely stalled disk worker. Because it uses a non-daemon thread to avoid abandoning an accepted durable transaction, an unresponsive I/O path can prevent a normal JVM exit. R427 also caught only `Exception`, not more severe `Error` categories: a synthetic assertion failure after writing could leave a pending request without a delivered uncertain receipt, or a failed owner-close could leave the close Future uncompleted.

## Implemented changes

**Public coordinator:** `tests/fixtures/r427/R427AsyncDeleteCoordinator.java` (independent Java 11 design, **not** recovered private code).

- `closeWithDeadline(duration, unit)` accepts a strictly positive deadline **from Swing EDT only**, calls the existing ordered `closeAsync()`, and returns `CompletableFuture<CloseObservation>` with **three disjoint statuses**:
  - `RELEASE_CONFIRMED`: the Store adapter's `closeOwner()` returned normally;
  - `RELEASE_UNCERTAIN`: `closeOwner()` raised a Throwable and lock state is unknown;
  - `UNCONFIRMED_AT_DEADLINE`: the original close operation has not completed *as observed at the deadline*. **This is not proof the lock is held or released**.
- Deadline scheduling uses Java 11 `CompletableFuture.delayedExecutor` and completes its observation **on Swing EDT** via `invokeLater`. It never invokes `shutdownNow`, interrupts the worker, invokes a second owner release, deletes any history marker, or modifies the original `closeFuture`. An overdue observation cannot authorize a restart, a new owner, a file cleanup or JAR release.
- After an overdue result, the **original** `closeFuture` may still eventually complete, and `View.ownerClosed(Throwable)` still reports the final result. A second observer of an already completed close may return the final status. No owner lock is released because of the deadline.
- An exception or `Error` after a possible Store write now conservatively maps to `UNCERTAIN`, quarantines further delete requests, and never marks a panel row deleted. This is *best-effort in a live JVM*; a real VM-wide failure (OOM, kill or crash) cannot be safely recovered using this prototype alone.
- A `closeOwner()` `Error`, not just an Exception, completes the original close Future **exceptionally**, quarantines the session and reports the original Throwable to Swing; owner release is **not** claimed successful.

### Performance and safety trade-off

**This is a bounded *status observation*, not a bounded shutdown or forced lock takeover.** The managed non-daemon I/O worker may still prevent process termination if the filesystem hangs permanently. Safe production escalation needs an explicit owner decision, filesystem-level recovery policy, and journal ownership/epoch evidence. An artificial timeout followed by `shutdownNow()` or `FileLock.release()` while disk writes can be pending would be an unsafe workaround and was not introduced.

A real Store adapter must still check the R419 lease and R411 journal state at the durable commit boundary, persist ambiguous-result quarantine across restart, and coordinate the existing final-save/lease-close path.

## Public synthetic tests

`tests/fixtures/r427/R427AsyncDeleteHarness.java` adds deterministic, controlled tests against an independently authored fake Store:

1. Deliberately hold an in-flight I/O worker past the requested deadline: observation returns `UNCONFIRMED_AT_DEADLINE` on EDT; ownership is **not** released, no new delete request is accepted, Swing remains responsive; after releasing the test latch, the original close completes and a new observation returns `RELEASE_CONFIRMED`.
2. Immediate no-pending close yields `RELEASE_CONFIRMED`.
3. Store `closeOwner()` throwing a RuntimeException yields `RELEASE_UNCERTAIN`, original close Future completes exceptionally and quarantine is active.
4. Store `closeOwner()` throwing an `AssertionError` has the same fail-closed result.
5. Store throwing an `AssertionError` **after** a synthetic committed write yields `UNCERTAIN`, quarantines, never changes UI and disallows blind retry.
6. Zero-length or null-unit deadlines are refused before closing or submitting work.

`tests/test_v309_r428_shutdown_observer.py` runs those **six** real-JVM/EDT scenarios and six static gate checks. The existing R427 22-test suite is inherited and re-run when the modified synthetic Java fixture triggers the R427 workflow. Tests use **only** invented direct TEMP paths and `javac --release 11`.

**Hosted:** dedicated Windows/Ubuntu × Python 3.11/3.13 + JDK21 CI, separate Recovery CI. Only claim success after reviewing final workflow job conclusions.

## Private integration blockers

Desktop Commander has already explicitly paused owner commands due to the monthly usage limit; do **not** retry or reconnect. No actual `LootHistoryStore.java` or `LootTrackerPlugin.java` has been edited/compiled/executed, no real history has been opened, no game/client JAR has been deployed, and no v312/FPS improvement has been measured. R422 private multiprocess acceptance, R425/R426 full 1,278-source private compilation and real Swing plugin lifecycle tests remain pending.

**Do not merge R428 or enable history cleanup, actual UI deletion, automatic journal reconciliation, or release.** The public coordinator remains a research prototype until the recovered private adapter has been inspected, implemented and validated in isolation against fake histories before any runtime acceptance.
