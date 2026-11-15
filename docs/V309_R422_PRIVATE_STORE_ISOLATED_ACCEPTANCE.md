# R422 — real reconstructed LootHistoryStore isolated acceptance

**Repository:** Trexzo/SpawnPK-Client
**Stacked on:** R421 draft PR #1217
**Status:** DRAFT / UNMERGED. No private release, client execution, production data changes, or marker recovery authorized.

## Why R422 differs from R418–R421

The earlier public Java/Python tests exercised independently invented file-lock, restart and UI-reconciliation models. R421 additionally compiled and SHA-gated the owner-private recovered Java source, but compilation is not behavioral acceptance. **R422 executes the actual private compiled `rs.plugins.loottracker.LootHistoryStore` class directly** through a public-safe, owner-only Java acceptance harness, using exclusively synthetic scratch histories under Windows TEMP. It does not load or start the SpawnPK game client or construct `LootTrackerPlugin` and is NOT full game/UI lifecycle acceptance.

## Owner-private actual-class evidence

The real R421 compiled class was loaded from the isolated owner TEMP source build, not from any deployed game or real player history. Test harness compilation used installed JDK21 `javac --release 11`, the R421 private class tree and its existing local dependency JARs.

- **Actual private compiled `LootHistoryStore` selftest: 73/73 assertions PASS, exit 0.**
- Actual private `LootHistoryStore.class` SHA-256 pinned to: `65272371272fdcf9142095880a042aa007a9a088f93c969a57878188fae37a09`.
- Test methods invoked the actual `LootHistoryStore(String)` TEMP-directory constructor, `r421PrepareHistoryDirectoryForLease()`, `r419ActivateOwner()`, `r411StageState()`, `loadForMerge()`, `saveWithReceipt(Collections.emptyList())`, `clearWithReceipt()`, and `r419CloseOwner()`, plus a deliberately limited reflective invocation of the private `r419WithOwner(Runnable)` to simulate held-I/O shutdown in the scratch process.
- Verified successful fresh one-leaf preparation, clean empty synthetic JSON write/read/clear, two same-process store owners' OS-lock conflict, refusal of nonowner read/write/clear, release/reacquisition, blocked action versus concurrent closer, cancellation fence after release, preservation of invented stage/intent/ack/ack-stage bytes, and refusal of absent-parent and regular-file leaf paths. Windows symlink creation was unavailable and was explicitly marked optional.
- The isolated Java invocation produced **multiple SLF4J binding** warnings because both existing private dependency JARs contain a binder; the 73 assertions still passed. No logging-binding cleanup or distribution change was made.
- **No real SpawnPK game client was started. No real loot-history file was opened, replaced, cleared or migrated. No private JAR was repackaged or installed.**

The private test was executed in a new synthetic `R422-Synthetic-Store-20261115` directory. The public harness checks that its scratch root remains inside `java.io.tmpdir` and that its basename starts with `R422-Synthetic-`.

## Actual private cross-process run: partially verified, NOT complete

A separate public Python orchestrator `tools/r422/run_private_store_acceptance.py` was invoked against the exact owner-private class and SHA pin. The first run advanced through real OS-lock subprocess contention, owner release, reacquisition and JVM `Runtime.halt(77)` crash/reacquisition checks, then **REFUSED the `actual_store_first_run_creates_leaf_and_acquires` case** because the public Java harness incorrectly required its named synthetic TEMP root to exist *before* calling the first-run directory-creation method. The restriction was corrected in the public harness: it now also allows exactly one absent final synthetic leaf provided its direct parent is an existing real directory, while retaining TEMP-prefix and nofollow restrictions.

**The corrected multi-process orchestrator has NOT been rerun against the real private classes.** Remote Desktop Commander reported its monthly usage quota exhausted and explicitly paused calls when that rerun was attempted. No attempt was made to bypass its quota, reconnect, or claim the real multi-process suite completed. The corrected harness remains available for independent owner-local repeatability checks.

## Public-only CI — NOT private-class acceptance

The GitHub branch publishes only:

- `tests/fixtures/r422/R422ActualStoreAcceptance.java`: public-safe, explicit-TEMP acceptance test harness; references private class APIs but contains **no recovered implementation**;
- `tools/r422/run_private_store_acceptance.py`: SHA-pinned owner-local process runner that refuses wrong class hashes before creating any scratch state; preserves synthetic artifacts for audit;
- `tests/fixtures/r422/R422SyntheticStoreStub.java`: independently invented public-only stand-in matching the harness's narrow store API, **never used as private client source**;
- `tests/test_v309_r422_public_harness.py`: subprocess and negative-control tests against that synthetic stand-in; checks private-class digest pinning, non-synthetic TEMP refusal, held-owner release, crash, first-run leaf and preservation of fabricated markers;
- `.github/workflows/v309-r422-public-harness.yml`: hosted Windows/Ubuntu × Python 3.11/3.13 JDK21 public-only harness-test matrix.

**Hosted public tests are not evidence of game or recovered-client behavior.** In particular the stand-in does not reproduce Gson serialization, R415 delete-intent durability, EDT callbacks or load-history merge semantics. Hosted CI results should be reported separately from actual owner-private R421 selftest.

## Outstanding blockers and R423 target

1. Corrected actual private cross-process test rerun is pending owner-device access. **Do not mark R422 full process acceptance PASS** on public synthetic CI alone.
2. The **actual reconstructed `LootTrackerPlugin` Swing restore/startup/shutdown lifecycle** remains unexecuted. Store-level tests cannot prove no stale EDT callback, deadlock, missing clear generation or session rollback.
3. R421's one-level directory preflight is not an anchored openat-style hostile path-swap defense. The game-global `Class307.method121()` still has its own mkdir behavior for unrelated callers.
4. R420 bounded retry can still time out under sustained lock contention.
5. Confirmed per-row/source/type deletion, Clear all and shutdown final persist can still perform blocking disk I/O on Swing EDT. No FPS or frozen-window fix claimed.
6. R415–R417 history intent/ack evidence remains quarantined. No actual restart adoption, no marker cleanup, no permission to resume previously fenced writes, no durable power-loss proof or v312 runtime acceptance.

**Keep R422 draft/unmerged, private candidate uninstalled, and release gate CLOSED.** Once owner-device access is available, run the corrected process suite against the SHA-pinned actual R421 class again, then use a restricted isolated event-dispatch test harness for plugin lifecycle and UI-safe disk receipts before any recovery re-enable.
