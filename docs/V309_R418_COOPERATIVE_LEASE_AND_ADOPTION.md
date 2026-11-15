# R418 — cooperative writer-lease research, epoch fencing and passive UI reconciliation

**Repo:** Trexzo/SpawnPK-Client
**Stacked on:** R417 draft PR #1213
**Status:** DRAFT / UNMERGED. Private-client execution and release gates CLOSED.

## Source-backed problem

R417 refuses unresolved acknowledgment sidecars, and R415/R416 validate the committed-after-delete image. R401's monitor only serializes writers inside a single plugin instance. Two separate Java processes could still write the same history file. A historical lock-file path or old timestamp does not establish that an OS lock is held.

## Narrow isolated owner-private source candidate

An exact R417 owner-TEMP source copy was made to:

R418-Private-Dormant-Cooperative-Lease/Source-Candidate-R418

Exactly one recovered Java source file changes: rs/plugins/loottracker/LootHistoryStore.java.

Added, but **not yet called by any actual client path**:

- r418TryAcquireCooperativeLease(): nonblocking FileChannel.tryLock() on a persistent `loot-history.writer.lock` filename. It requires a real, no-follow parent directory and refuses nonregular existing lock path/symlink or errors. It never deletes the lock path.
- Nested R418CooperativeLease implements AutoCloseable, owns a random UUID session token, tests released/lock validity/expected token, and serializes per-session action admission with close under a single monitor.
- close() marks the token revoked **before** releasing the OS lock and closing its channel. Duplicate close is harmless.
- Busy/overlapping/unreadable/unsupported lock attempts fail closed. No blocking wait loop on EDT.

This is a **dormant** API; it does not yet protect a live save, restore, delete, merge, or game callback. No claim of runtime multi-client safety is made.

### Private owner-Windows evidence

- JDK21 javac --release 11: **1,277 Java sources to 1,394 compiled class files PASS**.
- Exact R417-to-R418 source delta: one modified source.
- Exact compiled inventory: changed LootHistoryStore.class, added only LootHistoryStore$R418CooperativeLease.class; no removed classes or unrelated modifications.
- Private source SHA256 before: df49d39722f1073ded0368df5446f531aa86c1926259c17bd9145db278e05f25
- Private source SHA256 after: 929cd9d734cdd95fdcdf65325a5f894e22fba6426350c3d5e300d5a5b1d30714
- Read-only pinned actual owner-private audit: **R418_PRIVATE_DORMANT_LEASE_STATIC_GATE_PASS**, exit 0.
- No original client launched, no production history/cache modified, no private JAR distributed or private recovered source/classes uploaded.

## Independent public synthetic test models

All GitHub PR files contain invented fixture data and tests only.

1. Java 11 standalone R418SingleWriterModel holds a FileLock continuously while its UUID session is active; concurrent processes contend for an actual OS lock on **fabricated TEMP folders**. It never writes loot-history files or cleans markers. Python cross-process tests cover release, abrupt JVM halt, stale lock path, same/different directories, concurrent holders, UUID rotation, symlink rejection and preservation of fabricated intent/ack files.
2. Python adoption_contract.py models a read-only staged candidate and an in-memory mock panel. Before applying an entire image it rechecks session epoch, marker/hash, canonical schema and absence of pending local edits. Same-title independent records are preserved; repeated adoption is idempotent. Neither simulated adoption nor a valid synthetic ACK can enable a normal history write. The Java lease and Python fake panel **are not coupled**; they do not demonstrate end-to-end lease ownership across a Swing UI transaction.
3. Read-only SHA-pinned exact private-source/class verifier and synthetic negative controls test refusal of missing NOFOLLOW, blocking lock substitution, wrong lock name, missing revocation, unsafe lock cleanup, wrong SHA pins, extra classes and old ack-gate removal.

Local standalone Linux Java/Python lock-model run: 22/22 Python tests PASS plus 18 Java internal assertions. Owner private Java compile, class comparison and actual static-gate checks PASS. The Python adoption and auditor test suites require their own independent hosted verification before claiming success.

## Key limitations and release blockers

A file lock protects **cooperating processes that honor the same filesystem inode**; it does not stop an arbitrary foreign writer, lock-file path replacement, network filesystem edge cases or malicious symlink races. Do not delete or rotate the lock path while held. A file lock by itself is not a session-transaction protocol. The model offers no directory-fsync or physical power-loss durability proof.

No private Swing lifecycle integration, no proof of v309/312 parity, no cross-process runtime test of the recovered Java class, no no-restart live acceptance, no automated marker adoption/cleanup and no resolved startup-freeze root cause. Existing confirmed deletes still perform disk I/O on EDT. This stage **does not release** previously quarantined history or allow further writes.

**Keep draft, unmerged, and never deploy the private candidate.** R419 should first attach owner lease lifecycle and generation fencing on a non-EDT path in an isolated client harness, then test crash, shutdown, duplicate client, stale callback, and UI restore/ack ordering. Only after those checks can any marker cleanup or routine write resumption be considered.
