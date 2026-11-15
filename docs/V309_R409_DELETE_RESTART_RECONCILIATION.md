# R409 — file-backed delete intent and restart reconciliation (synthetic only)

**Repository:** Trexzo/SpawnPK-Client  
**Stack:** directly on R408 draft PR #1204  
**Status:** DRAFT / UNMERGED; **no owner-private R409 source change or new JAR**. This is a portable synthetic filesystem protocol and passive inspection of unchanged R407 source/class state.

## Why R409 is needed

R408 established a safe ordering goal for asynchronous confirmed edits:
admit the request on EDT, freeze nondeleted records on a worker,
write the history in serialized file-lock order, and only remove
confirmed UI rows after a successful disk receipt.

The R408 model also reproduced an unresolved **commit-before-EDT-ack**
window. The disk file can already contain the deletion when a plugin
stops or restarts before the EDT receives the success callback.
Retained UI state may still contain the supposedly deleted row.
A subsequent normal save could recreate the row on disk unless
startup reconciles the committed document with an explicit durable
transaction marker.

R409 prototypes that reconciliation using **only invented integer
row IDs and real throwaway filesystem paths**. It does not read or
modify the owner's actual loot history.

## File-backed synthetic sidecar protocol

The standalone Java 11 fixture
\`tests/fixtures/r409/R409DurableDeleteReconcileSynthetic.java\`
creates its own TEMP directory and a tiny text file
\`invented-history.txt\`. This is **not** the private client's JSON
history format.

For each destructive transaction, under a single synthetic
\`fileGate\`:

1. Require a **CLEAN** starting state with no unresolved journal or
   orphan staging files. Reject absent delete targets and refuse
   a second edit until the first receipt is reconciled.
2. Freeze the next serialized history image. Compute SHA-256
   digests of the existing and proposed exact file bytes.
3. Write a canonical version-1 sidecar intent with a local serial,
   a randomly generated UUID nonce, the before-image digest and
   the proposed after-image digest. Force the temporary intent
   through \`FileChannel.force(true)\`, then **require an atomic
   rename** to its destination; if unsupported, **refuse rather
   than downgrade to a non-atomic move**.
4. Write and force the exact proposed history bytes into a second
   temporary file, check that the actual before-image hash has not
   changed, then atomically rename over the history.
5. **Do not announce successful deletion merely because the
   worker ran.** The UI acknowledgment must match that unique
   transaction nonce and both before/after digests and confirm
   that the current file is precisely the proposed image.
6. Before removing a sidecar on normal acknowledgment or
   recovered restart, require the UI to have adopted **exactly
   the authoritative disk image**. A stale, null or missing
   UI image cannot authorize removing the recovery marker.
   Cleanup is a separate step after this check.

The nonce prevents an old EDT callback from accidentally
acknowledging a different deletion after a process restart
reuses an in-memory counter value. The SHA-256 values provide
accidental-change/corruption checks; they are **not authenticated
MACs or proof against an adversary who can edit both files**.

### Startup read-only classification

| File and marker state | Classification | Required behavior |
| --- | --- | --- |
| No marker, canonical valid file or absent file | \`CLEAN\` | Ordinary load may proceed |
| Valid marker and current bytes equal *before* digest | \`ABORTED_BEFORE_REPLACE\` | Restore original UI state; only then clear marker |
| Valid marker and current bytes equal *after* digest | \`COMMITTED_BEFORE_ACK\` | Restore committed UI state; only then clear marker |
| Invalid/oversize marker, invalid history, mismatch with both hashes, orphan \`.tmp\` file | \`QUARANTINED\` | Preserve files, refuse automatic edits and request deliberate recovery |

Re-running the read-only recovery classification never modifies the
file or journal. An interrupted cleanup can safely be repeated after
the matching history has actually been loaded into the UI.
An ambiguous state is **not** silently treated as success or reverted.

## Important limitation: actual private move helper is weaker

The owner-private R407 source was independently inspected
**read-only**, including the exact existing
\`rs/plugins/loottracker/AtomicFileReplace.java\` helper.

The existing \`LootHistoryStore\` writes a version-1
\`loot-history.json\` using a temporary \`.tmp\` file, then calls
\`AtomicFileReplace.move(temp, file)\`. Although the helper
first attempts \`StandardCopyOption.ATOMIC_MOVE\`, it **catches
\`AtomicMoveNotSupportedException\` and falls back to a normal
\`REPLACE_EXISTING\` move**. This fallback is not guaranteed atomic.

The current store also writes through a buffered stream without
an explicit \`FileChannel.force(true)\` for its temporary history,
and does not explicitly force the containing directory metadata.
It contains **no versioned delete intent, commit/ack marker, or
restart reconciliation**.

Thus the R409 model's strict atomic move and forced-file ordering
**do not apply to the current private client**. A later integration
would need to revise or isolate the affected write helper and
the storage lifecycle first. The current R407 private candidate
must not be described as crash-safe or as having R409 enabled.

Directory metadata forcing is optional/best-effort in the
synthetic model because not all platforms accept a directory
\`FileChannel\`. Even where calls appear to succeed, **sudden power
loss and storage-controller reordering are not proven**.
This protocol is evidence about recoverability across **normal
process termination and simulated interruption windows**, not
certification of physical power-failure durability.

## Owner Windows verification

- R409 actual unchanged private R407 source: **1,277 Java files**,
  **1,388 compiled classes**. Its existing five Loot Tracker source
  and seven class byte differences against SHA-pinned R381 remain
  unchanged. The original atomic move helper is byte-identical
  to the pinned original.
- Public SHA-pinned read-only checker
  \`tools/r409/audit_restart_reconcile_prerequisites.py\` run on
  those actual private trees:
  **\`R409_PRIVATE_RESTART_DURABILITY_GAPS_CONFIRMED\`**, exit 0.
  This is a positive result for **detecting the missing durability
  primitives**, not an approval of the current writer.
- **37/37 Python** invented source/class negative and
  integrity checks passed locally.
- JDK21 \`javac --release 11\` compiled the standalone synthetic
  fixture. **34/34 file-backed Java cases** passed locally,
  repeated **5/5 consecutive runs**.
- Separate actual Java process test: one **synthetic** JVM wrote a
  new history image, then deliberately exited nonzero after the
  atomic rename without acknowledgment. A fresh JVM reopened the
  same throwaway files and returned the exact classification
  **\`R409_CHILD_RECOVERY_COMMITTED_BEFORE_ACK\`**. The resulting
  history contained the confirmed post-delete rows.
- Test faults include prepare-stage temporary file, prepared
  manifest, forced but unmoved history temp, committed but
  unacknowledged file, acknowledgment before journal cleanup,
  unexpected modified history, corrupt/oversized intent, missing
  file, bad file schema, journal replay, deletion of duplicate
  synthetic rows, stale callback after counter reuse, unrelated
  synthetic thread contenders, and refusal to erase the marker
  before the recovered UI snapshot matches.

These tests never open the private game, its history, its config
directory, or any live user data. The synthetic files are created
within explicitly controlled TEMP directories.

## Remaining release blockers and next step

**Do not integrate R409 into the actual client yet.** An R410+
candidate must explicitly address the current non-atomic fallback,
file and directory force policies on Windows, bounded validated
journal parsing, interprocess writer conflicts, and a minimal
stable record identity/mutation snapshot contract. Integrate the
recovery check **before any ordinary startup autosave**, with
unresolved state blocking automatic rewrites and a visible
success/failure/needs-recovery UI.

Further runtime prerequisites include handling unexpected exceptions
during the EDT callback, plugin restart after a committed delete,
new loot arriving during the worker write, ambiguous I/O failures,
and clear-all competing with an outstanding edit. Power-loss
testing requires a suitable controlled environment; synthetic
process crashes cannot substitute for it.

No actual original client runtime, restricted guest acceptance,
v312 compatibility, startup-freeze root cause, durability across
machine power loss, or full client state equivalence has been proven.
No R409 private source files, class files or JAR were produced.
**Keep this PR draft and unmerged; private launch, release, merge
and distribution gates remain closed.**
