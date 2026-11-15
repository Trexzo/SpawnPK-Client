# R420 — bounded background lease retry and adversarial TEMP fault injection

**Repository:** Trexzo/SpawnPK-Client
**Stacked on:** R419 draft PR #1215
**Status:** DRAFT / UNMERGED. Private release and live-game runtime gates remain CLOSED.

## Confirmed R419 blocker

The R419 restart worker called `restoreStore.r419ActivateOwner()` exactly once. The previous process could still own the OS FileLock briefly while its daemon shutdown reaper was completing; a new session's restore immediately failed even if ownership was released milliseconds later. Separate known blockers include a missing history directory on first launch and synchronous confirmed deletes/Clear all on Swing EDT. R420 addresses **only** the transient lock contention case.

## Isolated owner-private R420 candidate

Fresh copy of `R419-Private-Leased-History-Lifecycle/Source-Candidate-R419` to:

`SpawnPK-R386-Isolated-Acceptance/R420-Private-Bounded-Lease-Retry/Source-Candidate-R420`

Exactly one private Java source changed: `rs/plugins/loottracker/LootTrackerPlugin.java`. `LootHistoryStore.java`, its lease API, journal, history schema and all existing store classes are unchanged.

New `r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation)` is called **only by the existing dedicated background history restore thread**, replacing its one-shot `r419ActivateOwner()` call.

- Rejects invocation on Swing EDT.
- Five finite nonblocking OS-lock attempts using exact delays **0, 75, 150, 300, 450 ms** (total potential sleep about **975 ms**).
- Sleep is performed **without holding** `r395HistoryGate`, `r401FileGate` or the Swing panel monitor.
- Before **every** attempt, checks uninterrupted worker, same `r395HistoryGeneration`, `r399AcceptingDrops`, plugin singleton identity and `historyStore` instance identity.
- Interruption restores the thread interrupt flag and refuses rather than retrying further.
- After a successful acquisition, the existing R419 post-acquire session recheck still runs before any legacy cleanup or history read. A stale candidate releases its owner.
- Exhaustion refuses to restore; it does not override any journal quarantine, permit unleased writes or delete any marker.
- It does **not** bootstrap an absent history directory or provide an infinite retry.

## Actual owner Windows private evidence

- JDK 21 `javac --release 11`: **1,277 private Java sources → 1,394 class files PASS**.
- Exact source SHA delta vs R419: **only LootTrackerPlugin.java modified**. Original plugin SHA256 `e8684505fcfaa4967ea2fa4a69a8e11d580256fe415f2f4d90ad60559c35b7b8`; R420 plugin SHA256 `844451db7874ff54eb90cd5ccc93591624bd33a3b8a6e5c13e3a60787b923c3d`.
- Exhaustive compiled-class SHA comparison: **only LootTrackerPlugin.class changed**. Zero added, removed or unrelated classes; LootHistoryStore.class remained byte-identical.
- Read-only SHA-pinned auditor executed on the actual owner-private source/class trees: **`R420_PRIVATE_BOUNDED_RETRY_STATIC_GATE_PASS`**, exit 0.
- No actual private client launched, no JAR packaged or installed, and no production v312/history/cache read or modified.

## Public-only TEMP fault research

All branch files are public-safe independently invented models/fixtures, not recovered client source.

- `tests/fixtures/r420/R420RetryFaultModel.java` models finite worker retry using R418's real Java 11 `FileChannel.tryLock` against fabricated TEMP directories, simulated session epochs, cancellation, JVM interruption, an EDT refusal and a held synthetic action racing an async lease closer.
- `tests/test_v309_r420_retry_fault.py` invokes actual competing Java subprocesses. Scenarios include busy→release during backoff, permanent contention, process crash, expired previous session, interrupt preservation, refusal from Swing EDT, locked action while shutdown waits and no writes to fabricated history, intent, ack or staged files.
- `tools/r420/audit_private_bounded_retry.py` performs read-only exact SHA-pinned private-source/class inventory validation, verifies the retry remains worker-only, enforces bounded delays and ordering, requires original R419 session admission and detects duplicate pre-lease restore I/O.
- `tests/test_v309_r420_retry_audit.py` contains fabricated positive and negative controls for removing epoch/owner/EDT/interrupt gates, unbounded loops, moved sleep into the monitor, unexpected class changes and wrongly replaced original private source.

**Owner Windows public tests:** **48 total, 47 PASS, 1 optional symlink SKIP, 0 FAIL** under Python 3.12 + JDK21. Real original-client and real Swing event-handler runtime acceptance are not included. The separate hosted Windows/Ubuntu x Python 3.11/3.13 JDK21 workflow must be checked independently.

## Remaining risks / release blockers

1. A competing or crashed process could hold a lock for longer than 975 ms; R420 then safely refuses. It does not guarantee successful restore.
2. New installs without an already-existing parent history directory still fail lease admission. Creating directories safely requires separate no-follow/path-provenance and failure tests.
3. The R419 daemon release thread can still race a rapid restart, and old workers can hold file/lease action monitors. Synthetic races cannot prove private-client thread deadlock freedom.
4. Real confirmed per-row/source/type deletes and Clear all remain synchronous and can still block Swing's EDT. No FPS/latency improvement is claimed.
5. No automatic journal restart acknowledgment, marker cleanup, recovery of partial writes or permission to resume previously quarantined history writes.
6. Existing lease protects cooperating processes on the same stable lock inode, not unexpected foreign writers or active lock-path replacement.
7. No original game runtime, physical mouse/GUI test, deployed v312 compatibility acceptance, power-loss test or production data validation.

**Keep this PR draft/unmerged; do not launch or deploy the private R420 candidate.**

**R421 proposed next:** safely bootstrap an absent history directory on the off-EDT worker, and test retry/stop interleavings under a restricted isolated Java harness. Only after verified lifecycle acceptance should asynchronous EDT deletion receipts or automatic journal reconciliation be attempted.
