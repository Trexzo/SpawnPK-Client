# R429 — synthetic persistent uncertain-write evidence and restart fence

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R428 draft PR #1224  
**Status:** public-only research, DRAFT / UNMERGED. Release and live-client change gates CLOSED.

## Motivation

R427/R428 implemented a Java 11 **public synthetic** asynchronous deletion-receipt coordinator. It quarantines ambiguous post-write outcomes in memory and reports uncertain owner release without forcibly dropping locks. That does not survive process termination. After JVM restart, the in-memory `quarantined` flag is lost, and automatic replay of a previous delete could be unsafe unless a persistent, verified record exists **before** the underlying write begins.

The actual private Loot Tracker already has the separate R415–R417 intent/ack protocol and R419 OS lease; R429 must NOT silently introduce another production file format or bypass those established guards. Without owner-private source access, we cannot implement a correct adapter yet.

## Added independently authored Java 11 research fixture

`tests/fixtures/r429/R429SyntheticRestartFence.java` is restricted to directories named `R429-Synthetic-*` **directly under the Java TEMP folder**; it does not import any client code or recognize a real player history path.

It models a conservative write-ahead evidence gate using the synthetic file `R429-synthetic-intent.ledger`:

- **Explicit initialization only.** `CREATE_NEW` opens a 256-byte file containing two fixed 128-byte slots. Initialization fails if a ledger already exists; none of the CLI operations includes a reset/delete command.
- Each slot contains a versioned magic header, monotonically increasing sequence, state (`EMPTY`, `PENDING`, `CONFIRMED`), synthetic operation UUID and a CRC32 checksum, with reserved bytes required to remain zero. The whole file is required to have its exact expected size.
- **No-follow traversal preflight:** all directory ancestors must be real directories, the ledger must be a regular file without symlink traversal, and the prior `loot-history.json.tmp` and delete intent/ack evidence paths must be absent. Present, unreadable or dangling-symlink markers block access rather than being silently removed.
- A nonblocking **per-file JVM/OS `FileLock`** refuses concurrent synthetic writers. This is only a local cooperative lock for the test ledger and is **not** an R419 lifetime writer lease.
- `begin(UUID)` demands the latest valid state is `EMPTY`, writes the alternate slot as `PENDING`, calls `FileChannel.force(true)`, rereads the written slot, and only then permits a *hypothetical* Store commit. Neither `begin` nor the fixture performs deletion of real or synthetic history records.
- When both slots are present, a newer valid sequence wins. **Any nonzero malformed slot refuses the whole ledger**, even if another older slot is valid. A torn newer write must not cause a fallback to a previous `EMPTY` record.
- A simulated `Runtime.halt(77)` occurs *after* the intent has been written and forced. A fresh JVM still observes `PENDING` and refuses a new `begin`; the test never treats a crash as an implicit refusal/rollback.
- `seal(UUID)` requires the exact pending operation and only models an external durable acknowledgment. It records `CONFIRMED` but **retains the evidence and still refuses any new transaction on subsequent restarts**. There is no automatic clearing, replay, resumption, or journal adoption.

### Crucial durability limitations

A forced file payload does **not** prove the **directory entry** was durably persisted across a sudden power cut; Windows and Linux expose different directory-flush semantics. R429 does not implement directory fsync, a pre-existing provisioned inode guarantee, a hardware power-loss test, a verified external commit receipt, or recovery from a torn ledger. Its CRC32 detects accidental corruption but is **not cryptographic authenticity**. It cannot resist a malicious process swapping the file or its ancestors between no-follow checks or ignoring the test lock.

**Do not describe this fixture as a production-ready crash-proof journal.** A future private adapter must use the actual R415–R417 journal/receipt format, enforce R419 lifetime ownership, persist evidence *before* disk mutations, and reject ambiguous state on restart until proven reconciliation is available.

## Public validation

`tests/test_v309_r429_restart_fence.py` compiles the fixture with `javac --release 11` and runs **26 synthetic-only Python-driven JVM tests**: explicit initialization, duplicate init rejection, forced pending intent and restart refusal, no-blind retry, synthetic crash with retained pending state, mismatched proof, retained confirmed evidence, corrupted/truncated records, unexpected padding, live competing JVM locks and release, invalid UUID/root paths, no-follow symlinks and unresolved preexisting journal markers. Canonical fabricated `loot-history.json` bytes remain unchanged throughout.

Dedicated GitHub workflow `v309-r429-durable-uncertain-restart-fence` covers **Windows and Ubuntu × Python 3.11 and 3.13 with JDK21**, separately from generic Recovery CI. Unsupported symlink privileges on Windows may produce explicit test skips; a skipped symlink case must never be counted as proof of symlink defense on that host.

A successful hosted run proves only synthetic test behavior and not actual owner-private code integration. The workflow must be independently verified on the final commit before claiming a pass.

## Remaining release blockers

1. **Desktop Commander access remains paused by its monthly usage limit**; no private R415–R417 source or live history was opened, modified or compiled in R429.
2. The actual `LootHistoryStore` adapter must consult existing pending intent/ack evidence under the R419 lease *before* exposing further write admission, persist an intent before a new delete, and generate a genuinely durable verified receipt after completion. Neither the actual store nor `LootTrackerPlugin` has been integrated.
3. The original UI/session version has to include every panel edit, confirm-delete path, group/source/type delete and shutdown final-save operation. R428's in-memory quarantine and deadline observer remain public prototypes.
4. The corrected R422 real-class cross-process rerun, R425/R426 full owner-private Java compile, actual Swing EDT lifecycle, power-failure recovery, and v312 runtime acceptance remain incomplete.
5. No automatic legacy deletion, evidence cleanup, source upload, JAR installation or production release is authorized. Keep all stacked PRs **draft and unmerged**.

**Next:** when authorized owner-PC access resumes, inspect existing R415–R417 format and build a read-only actual-store restart admission harness first; only then propose an exact private adapter. Do not copy this synthetic ledger into the real player cache.
