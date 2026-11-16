# R431 — journal-bound asynchronous owner test (public synthetic integration)

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R430 draft PR #1226  
**Status:** DRAFT / UNMERGED / NEVER DEPLOYED.

## Purpose and finding

R427–R428 created a public, Java 11 asynchronous deletion receipt coordinator with real Swing EDT dispatch, a single managed non-daemon I/O worker, owner-session and panel-version fencing, and ordered shutdown. R430 showed that the earlier, actual private R415 deletion path intentionally retains a persistent version-one delete-intent marker on success; R416 is only a passive restart schema validator, and R417 only gates ack/ack.tmp evidence. **There is no real private restart-adoption acknowledgment or safe subsequent-write unblock.**

R431 tests the consequence using a newly authored, **synthetic-only**, minimal Java `Store` adapter bound directly to the public R427 coordinator. R431 does **not** edit, import, compile, load or run recovered `LootHistoryStore.java`, `LootTrackerPlugin.java`, real loot files or installed client JARs.

## What is implemented

`tests/fixtures/r431/R431SyntheticJournalStore.java` provides a restricted implementation of `R427AsyncDeleteCoordinator.Store`. It has no game imports and validates a direct `R431-Synthetic-*` child of Java TEMP with no-follow ancestor checks. It accepts **only one invented `RECORD_IDS("synthetic-22")`** request. Any other delete kind, existing intent/ack/stage, R429 experimental ledger, unsafe history schema or missing session admission returns `REFUSED` with no write attempt.

The store holds a real cooperative OS `FileLock` from construction until `closeOwner()` returns, and refuses competing same-JVM and cross-JVM owner acquisition. This synthetic lock file is not the original R419 owner lease and does **not** establish production cross-process safety against uncooperative clients or malicious path swapping.

For a fabricated confirmed-deletion *research* operation, the worker models R415's ordering on separate TEMP files:

1. Prepare a new history stage using `CREATE_NEW` and `FileChannel.force(true)`; compare the old and proposed image SHA-256 values.
2. Prepare the exact existing **R415 version-one** marker format `v=1 / serial=1 / nonce / before / after` using `CREATE_NEW` and force it.
3. Recheck session admission, original history and stage immediately before publishing the sidecar. Once any stage was persisted, cancellation or error becomes `UNCERTAIN`, not a definite noncommit.
4. Publish the intent using **`Files.createLink(final,tmp)`** so an existing marker is never overwritten; remove only the owned temporary marker alias, not the permanent intent.
5. Attempt `Files.move(stage,history,ATOMIC_MOVE,REPLACE_EXISTING)` without removing the immutable intent.
6. Compare the new fabricated history bytes against the expected image and preserve the published marker on success.

**Crucial distinction:** Even after the synthetic atomic replacement completes, the adapter returns **`UNCERTAIN`, not `CONFIRMED`**, because R415/R416/R417 do not provide a fully adopted restart acknowledgment or proven directory-entry power-loss durability. R427 therefore leaves the UI unchanged and quarantines further deletes; a successful disk image and permission for continued writes are **different facts**. This is intentionally conservative, not a claim that the existing private confirmed-delete UI must behave exactly this way.

The adapter's synthetic `closeOwner()` does not set `isReleased=true` until both OS lock release and file-channel close have completed normally. A failed release remains **unknown**, not claimed successful.

No ack sidecar is created, no marker is cleaned, and no second automatic history write is authorized. A later `Store` instance observes the original final marker and refuses another transaction.

## Real Swing, JVM and cross-language public testing

`tests/fixtures/r431/R431JournalBoundAsyncHarness.java` uses actual Swing `invokeAndWait` and `R427AsyncDeleteCoordinator` requests, with deterministic fault hooks and held-worker latches. It verifies owner release runs *after* the in-flight commit and off EDT. `closeWithDeadline` reports an overdue operation, but cannot drop the lock or authorize a restart.

`tests/test_v309_r431_async_journal_bridge.py` compiles this independently authored Java source with `javac --release 11`, executes separate JVMs against fresh direct TEMP paths, and then calls the **existing public R417** classifier `tools.r417.restart_ack_model.inspect` to inspect the resulting actual marker/history bytes. The 21 tests cover:

- Complete synthetic staged/atomic replacement with a retained, R417-compatible v1 `COMMITTED_UNACKED_FENCED` marker and **no confirmed UI deletion**.
- A separate restarted JVM refusing the next persistent delete while preserving all existing marker/history bytes.
- Shutdown while the worker is held *after* final intent publication: no premature owner release, EDT responsiveness, no forced move; R417 subsequently sees unresolved staged evidence.
- Faults after stage force, intent-temp force, final no-clobber publication and atomic move, all preserving the necessary evidence and preventing blind retry.
- Session invalidation before any filesystem stage, a preexisting orphan ack, unsupported `CLEAR_ALL` and a symlinked intent, all refused without history mutation.
- Competing live JVM file-lock refusal; successful re-acquisition after orderly owner-close and after deliberately killing a synthetic owner process.
- A nonsynthetic root refusal, no real client imports/deployment, exact R415 intent format and repeated read-only classification without deleting evidence.
- A matching synthetic ACK **still** cannot allow another transaction or delete the original intent; two further JVM restarts keep the same permanent marker.
- A second actor inserting a foreign history stage **after preflight but before CREATE_NEW** causes an **UNCERTAIN** receipt, preserves the foreign stage, and leaves canonical history unmodified. The adapter marks an attempted persistent side effect **before** opening the stage; a failed stage create/force is not misreported as definite `REFUSED`.

The dedicated GitHub Actions workflow `v309-r431-journal-bound-async-owner` covers **Windows and Ubuntu × Python 3.11/3.13 with JDK21**, with exact final results requiring independent verification.

## Limits and private acceptance gates

This is not a private integration. The mock supports one invented record-id deletion, not actual `clearWithReceipt()`, per-source/type records, Gson DTOs, R419 owner epoch or the complete LootTrackerPlugin lifecycle. The synthetic adapter is not hostile filesystem race-proof. `force(true)` on newly created files and an atomic replace do not by themselves establish physical power-cut durability of directory entries. No actual private journal adoption, ack producer, marker clearing or automatic recovery is implemented.

The owner PC's Desktop Commander access remains quota-paused. **No private Java source/class files, production loot history, v312 client, game runtime or client distribution were touched.** Actual source-exact R415–R417 compatibility, R422 corrected cross-process acceptance, R425/R426 full 1,278-source compile, and real Swing shutdown-save ordering remain unverified.

**Next private step (when owner access resumes):** Run read-only R430 source admission audit and R425/R426 isolated compilation first, then map the real `persistHistory()` journal transition and plugin final-save path before adapting a single confirmed delete. Never deploy or enable cleanup on the strength of synthetic R431 results. All stacked PRs remain draft/unmerged; release gate CLOSED.
