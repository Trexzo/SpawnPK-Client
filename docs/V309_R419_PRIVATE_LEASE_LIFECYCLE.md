# R419 — isolated cooperative lease lifecycle and history entrypoint fences

**Repository:** Trexzo/SpawnPK-Client
**Stacked on:** R418 draft PR #1214
**Status:** DRAFT / UNMERGED. No private runtime launch, owner-client deployment, release or production write authorization.

## R418-to-R419 source finding

The R418 lease existed but was dormant, so `LootTrackerPlugin.startUp()` still called `historyStore.deleteStale()` before history restore and before taking any cross-process OS lock. Merely protecting background autosaves would not protect this startup cleanup, restore/merge, Clear all, or synchronous confirmed deletes.

## Isolated owner-private R419 candidate

A fresh copy of the R418 private source was created under the owner's Windows TEMP workspace:

`SpawnPK-R386-Isolated-Acceptance/R419-Private-Leased-History-Lifecycle/Source-Candidate-R419`

Exactly **two** Java source files were edited:

- `rs/plugins/loottracker/LootHistoryStore.java`
- `rs/plugins/loottracker/LootTrackerPlugin.java`

The store retains one long-lived R418 cooperative OS lease. A new owner activation method calls R418's nonblocking `FileChannel.tryLock()`. The lease is held through all history I/O action wrappers, not just checked before issuing file writes. Entry wrappers guard `deleteStale()`, `loadForMerge()`, both normal/confirmed save paths through `r415SaveWithReceipt()`, and `clearWithReceipt()`. The R411 stage admission now fails closed without current lease ownership while preserving R417's orphan acknowledgement/intent fences.

The plugin removes `deleteStale()` from synchronous startup. Its background history restore worker first tries to acquire ownership, then rechecks the captured plugin session/generation before performing legacy cleanup and reading history. If acquisition is busy or unsafe, restore is refused rather than falling back to the unleased writer.

The R399 session is invalidated on shutdown. An explicit shutdown-thread gate permits only the existing final save on its responsible thread; late asynchronous callbacks and stale panel deletes/clear requests are refused. After normal shutdown persistence, a daemon thread closes/revokes the old lease to avoid an additional synchronous wait on the client/EDT thread. This is *not* a guarantee of bounded shutdown latency, lossless data, successful future reacquisition or complete live-client lifecycle acceptance.

## Actual Windows private build and independent scope proof

- JDK21 `javac --release 11`: **1,277 Java sources → 1,394 compiled classes PASS**.
- Exhaustive byte comparison versus R418: **exactly two changed existing classes**, `LootHistoryStore.class` and `LootTrackerPlugin.class`. No new, removed, or unrelated changed classes.
- Read-only actual private-tree SHA-pinned auditor `tools/r419/audit_private_leased_lifecycle.py`: **R419_PRIVATE_OWNER_LEASE_LIFECYCLE_STATIC_GATE_PASS**, exit 0.
- R418 store source SHA256: `929cd9d734cdd95fdcdf65325a5f894e22fba6426350c3d5e300d5a5b1d30714`
- R419 store source SHA256: `3de16fab8f734846dc13d32cd55e3845387298d881c03de2701a7b4120309e79`
- R418 plugin source SHA256: `e54636668a72ace583534b4dca9d5b9477165c9b29b8c3dede64ffec2f5ebd2a`
- R419 plugin source SHA256: `e8684505fcfaa4967ea2fa4a69a8e11d580256fe415f2f4d90ad60559c35b7b8`
- No private client was launched, no production history inspected/modified, no v312 installation modified, and no recovered source/classes/JAR uploaded to GitHub.

The borrowed R418 compiler receipt's inherited `changed_private_sources` annotation is **not authoritative**. The independent actual R419 SHA-pinned source/class inventory and patch receipt both verify two changed sources and two changed classes.

## Public-only independent synthetic tests

The GitHub branch contains only invented Java/Python test models, a read-only source/class audit and documentation. The standalone Java 11 lifecycle model uses R418's real TEMP file-lock test helper and exercises session epochs, competing holders, post-stop callbacks, release/reacquisition and stale worker admission. A separate fabricated auditor suite exercises missing guards, premature cleanup, incorrect shutdown order and unleased write paths.

- Owner Windows local: **41/41 synthetic Python-driven cases PASS**, including standalone Java session assertions, and **R419 actual private SHA-pinned static gate PASS**.
- The initial audit incorrectly tolerated a *duplicate cleanup call before lease acquisition*. Synthetic negative test #20 exposed that structural false positive. The verifier now explicitly rejects duplicate owner activation, cleanup and load calls in the restore worker. Both the full synthetic suite and the actual private gate were rerun green.
- Hosted Windows/Ubuntu x Python 3.11/3.13 JDK21 jobs are configured but must be verified on final HEAD before claiming hosted PASS.

## Outstanding correctness and performance risks

1. **No original-client runtime acceptance:** source compilation and structural checks do not prove synchronized Java/Swing event-order correctness, deadlock freedom, recovery after failures, or that all unexpected callers are fenced.
2. **Busy lock/fresh directory:** startup currently has no automatic retry if another cooperating process holds the writer lock, or if the expected history directory does not already exist. Both conditions are intentionally fail-closed but could prevent ordinary history restoration on a fresh install or rapid same-process restart.
3. **Shutdown ordering:** asynchronous lease release can outlive the plugin stop and briefly prevent a new session acquiring ownership. A client shutdown, interrupted worker or process termination needs a dedicated lifecycle fault-injection harness.
4. **EDT I/O remains:** confirmed row/source/type deletion, Clear all and final saves can still wait synchronously on disk or the local file gate. R419 does **not** establish improved responsiveness or the cause of the original frozen window.
5. **No journal reconciliation or safe cleanup:** R415–R417 intents/acknowledgments still quarantine subsequent writes; R416's passive validated-image status is not adoption. No automatic marker deletion, journal acknowledgment or write unblocking.
6. **File-lock limits:** this protects cooperating processes on the same stable lock inode, not non-cooperating clients, lock-path replacement, unusual network filesystems, hostile writers or power failure.
7. **Version compatibility:** original v309 private-client runtime parity, deployed v312 acceptance, externally isolated guest tests and physical directory-fsync durability remain unverified.

**Keep draft and unmerged. Do not deploy, run the recovered private game client, merge, or distribute a JAR.**

**R420 priority:** separate process-lifecycle/EDT fault injection (acquire lost, rapid restart, shutdown during blocked save, clear while restore waits), then validated automatic retry and safe startup-directory admission on a test-only path; no journal cleanup until a complete restart-adoption acknowledgment protocol is verified.
