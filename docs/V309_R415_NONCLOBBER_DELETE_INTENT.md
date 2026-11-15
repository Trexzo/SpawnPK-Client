# R415 — no-clobber confirmed-deletion intent producer

**Repository:** Trexzo/SpawnPK-Client  
**Stack:** directly on R414 draft PR #1210  
**Status:** DRAFT / UNMERGED. **Private isolated source/build/static audit verified; private runtime/release NOT approved.**

## What changed from R414

R414 was a passive classifier for R409's version-1 history delete-intent marker.
R415 adds a producer on the **confirmed persistent deletion path only**, preserving
routine autosave's existing writer. The owner-private changes live in
\`rs/plugins/loottracker/LootHistoryStore.java\` and
\`rs/plugins/loottracker/LootTrackerPlugin.java\`.

When confirmed deletion invokes \`persistHistory()\`, the writer checks
the existing R411/R414 staging and marker admission, hashes the prior
canonical history, creates and **forces** the new history stage using
\`CREATE_NEW\`, and hashes that stage. If those images are equal, null,
unreadable or changed unexpectedly, it refuses the operation.

It then prepares a strictly bounded version-1 marker containing
\`v=1\`, \`serial=1\`, a lowercase UUID nonce, and the before/after
SHA-256 digests. The marker is written to a **new** temporary path,
\`FileChannel.force(true)\` is called, and the two history image hashes
are checked again before marker publication.

The owner-private marker producer publishes the final path using
**\`Files.createLink(final, temp)\`** instead of a replacing rename.
A pre-existing final marker cannot be overwritten. If the filesystem
does not support creating the hard link, publication **fails closed**.
Only the current transaction's newly owned temporary marker link
is removed after publication; any failed/unknown stage or final marker
is preserved.

The persistent marker must then classify as
\`ABORTED_BEFORE_REPLACE\` against the still-current old history image.
Both history images are rechecked again before attempting R410's
strict atomic replacement. Once replacement has been attempted,
R413's write disposition remains ambiguous on exception and does not
authorize speculative UI rollback.

**A successful marked confirmed deletion intentionally leaves the
marker in place and sets the existing unsafe-history gate.**
Further writes and persistent confirmed deletions are blocked until
a future authenticated, independently verified adoption/acknowledgment
design exists. This is a correctness-first research checkpoint,
**not usable production behavior**.

Regular autosaves, shutdown saves, Clear all, the price-cache path,
the R413 identity rollback and the R414 restart classifier remain
unchanged. UI-only deletions do not create a marker.

## Owner-private Windows evidence

The first remote execution attempt timed out when the connected PC
stopped responding. On reconnection, a **read-only check** confirmed
both R415 candidate Java files were still **byte-identical to R414**,
and no R415 patch receipt existed. The original script was not blindly
rerun.

Before applying the patch, the script's intended Java marker literal
was corrected: it would otherwise emit literal \`\\n\` characters rather
than real newline separators. The repaired script was executed in the
isolated owner TEMP workspace. The resulting Java source was checked
for the canonical newline sequences.

- JDK21 \`javac --release 11\` full compile: **PASS**,
  **1,277 Java source files → 1,392 class files**.
- Exact full byte comparison vs R414: **2 changed Java sources**,
  **2 changed existing compiled classes**,
  **0 added/removed classes**; every other Java/class file matches.
- Independently SHA-pinned original R381 source and reference-JAR
  custody hashes passed. Existing changes versus original R381
  remain confined to the eight established Loot Tracker classes.
- Public read-only actual-private-source auditor
  \`tools/r415/audit_private_intent_delta.py\` ran in owner TEMP
  against the private R414→R415 trees:
  **\`R415_PRIVATE_NONCLOBBER_INTENT_STATIC_GATE_PASS\`**, exit 0.
  It verifies marker newline serialization, force-before-publish,
  exclusivity, previous-stage fences, separate routine/confirmed
  writer paths, strict atomic replace, R413 phase handling and
  post-success refusal of future writes.
- Private custody-only JAR:
  \`R415-PRIVATE-DO-NOT-RUN-OR-SHARE.jar\`,
  SHA-256
  \`5981f8a0049135a16423c32f33ce01ee93f7810d5327277c950642b68f3212b4\`.
  Compiled and packaged **but never launched, installed, uploaded,
  shared or executed**.
- No production history, staging file, v312 client or
  friends' package was opened, modified or deployed.

**Owner TEMP path:** \`R415-Private-Nonclobber-Delete-Intent-Producer\`.
The exact source/class, static audit, compile and custody receipts are
preserved within that workspace. No private source or JAR is committed
to this public GitHub branch.

## Public independent regression evidence

The PR hosts:

- \`tests/fixtures/r415/R415NonClobberDeleteIntentSynthetic.java\`:
  an independently invented Java11-compatible real-TEMP-filesystem
  model with **24 mandatory scenarios**. It exercises forced stage
  and marker writes, hard-link collisions, interruption at each
  boundary, unknown/mismatching history images, no automatic final
  marker cleanup, strict atomic move failure, and a separate child
  JVM which exits after commit before a fresh JVM classifies it.
- \`tools/r415/audit_nonclobber_intent_synthetic.py\` plus
  **38 Python fabricated structural tests** for the public model.
- \`tools/r415/audit_private_intent_delta.py\` plus
  **25 Python fabricated SHA-pin, source/class inventory and
  negative controls**. The latter mocks only the semantics of an
  invented source corpus; the **actual** owner-private audit above
  was executed separately and unmocked.
- Hosted GitHub Actions: **Windows and Ubuntu × Python 3.11/3.13,
  JDK21, 4/4 dedicated jobs PASS**, including both Python suites
  and the standalone Java fixture.
- Separate Recovery CI for the previous revision completed
  successfully; CI status for subsequent commits must be checked
  independently.

No fabricated test claims to exercise the actual private game
classes, actual player loot JSON, native client startup, or a
physical power-loss recovery.

## Remaining blockers: NOT release-ready

The original client freeze and EDT stall root cause is not verified.
Confirmed persistent deletion still runs synchronously on Swing EDT
while holding the local \`r401FileGate\`. This milestone **does not**
improve responsiveness.

The marker remains after a successful deletion and will block future
history writes until a future milestone implements safe adoption and
acknowledgment. No automatic cleanup is authorized. A second
uncooperative process can race even repeated SHA-256 checks; the
current lock is intra-process only. SHA-256 is not an authentication
mechanism. The hard-link creation is not a proof of durable directory
metadata after abrupt power loss, and the protocol lacks durable
directory syncing.

A failed move after entering atomic replacement can leave UI/disk
state ambiguous. No fully verified restart handoff, marker provenance
proof, record-schema adoption, all-thread-schedule proof, restricted
guest client acceptance, original v309 behavioral parity or v312
compatibility evidence exists.

**R416 priority:** design the stateful, verified restart-adoption and
acknowledgment path, including history JSON schema verification, exact
intent-image revalidation and conservative handling of conflicting
or partial markers, *before* contemplating marker cleanup or
asynchronous confirmed deletes.

**Keep PR draft and unmerged. No private client launch, distribution,
release, deployment or automatic history recovery authorized.**
