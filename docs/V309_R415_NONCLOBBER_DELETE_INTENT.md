# R415 — no-clobber confirmed-deletion intent producer, synthetic verification

**Repository:** Trexzo/SpawnPK-Client  
**Stack:** directly on draft R414 PR #1210  
**Status:** DRAFT/UNMERGED. **The private R415 patch/build is NOT verified.**

## Why R415 is necessary

R414 integrated a read-only classifier for a version-1 delete-intent
marker, based on the earlier R409 synthetic protocol. A matching
before/after digest can distinguish an interruption before the
history move from an interruption after the history move but before
the UI received an acknowledgment. However, R414 creates **no**
intent marker. The mechanism cannot yet document a real deletion.

R415 develops the missing producer side **in a completely
independent, fabricated filesystem model**, while preserving a
fail-closed release policy. The public fixture uses a unique
TEMP directory, invented integer row IDs, and invented text
history, **not** the private client's JSON records or executable
Java code.

The owner's connected desktop became nonresponsive during the
attempt to apply an isolated R415 private patch. The remote
write/process request timed out without a confirmed result.
**Do not assume that patch applied, compiled or passed any
private static gate.** Before any subsequent remote retry, first
reconcile the existing workspace/receipt; do not reapply an
ambiguous side-effecting command blindly.

## Proposed write-side transaction order

A confirmed persistent panel deletion should occur under the
existing local \`r401FileGate\`. Nonpersistent UI-only edits,
routine autosaves, price-cache flushes and shutdown merges
must not implicitly create a delete intent.

The independent R415 Java fixture models:

1. Check that no final intent, prepared-intent temporary file
   or unexplained history stage exists. If any exists,
   **refuse** the edit.
2. Capture exact old main-image SHA-256 and stage the proposed
   post-delete image through \`CREATE_NEW\`, writing and
   forcing the temporary file. Never truncate an orphan.
3. Compute and validate the staged image hash, rejecting
   identical before/after images.
4. Write a canonical R409-compatible version-1 intent:
   \`v=1\`, \`serial=1\`, lowercase UUID nonce,
   \`before=ABSENT\` or SHA-256 digest, and
   \`after=\` SHA-256 digest. Write its own
   \`CREATE_NEW\` temporary file and \`FileChannel.force(true)\`.
5. Recheck the main and staged-image hashes. Publish the
   prepared marker using **\`Files.createLink(final,temp)\`**,
   a filesystem hard-link namespace creation that fails if
   the final marker already exists, without overwriting a
   conflicting marker. There is **no fallback** to an
   \`ATOMIC_MOVE + REPLACE_EXISTING\` for publishing the
   marker. If hard links are unsupported, fail closed.
6. Remove **only the known-new, current transaction's
   temporary marker link** after publication. If the
   process crashes before this step, both marker paths
   remain and the R414 classifier reports \`QUARANTINED\`.
   Never erase a pre-existing unidentified marker.
7. Require the published marker to classify as
   \`ABORTED_BEFORE_REPLACE\` while the original history
   still exists; recheck both history images again before
   attempting replacement.
8. Attempt strict \`ATOMIC_MOVE + REPLACE_EXISTING\`
   of the forced staged history into the canonical file.
   Once the move is attempted, an exception leaves an
   **ambiguous** commit disposition: never assume the
   old history remains authoritative.
9. If successful, acknowledge the deletion in the
   current synthetic session but retain the final marker.
   **Block every later save** until a distinct, verified
   restart-adoption and marker-acknowledgment protocol
   is integrated.

The hard-link publication deliberately differs from
R409's replacing atomic-rename marker prototype because
that helper could overwrite a newly published foreign
intent marker. \`Files.createLink\` has platform and
filesystem constraints; it must not be described as
universally supported or as fully durable across sudden
power failure.

**This cannot be deployed as-is.** By design, even a
successful confirmed deletion leaves an unresolved marker
and disables subsequent history writes. It is only a
partial transaction protocol, not the finished owner UI
recovery workflow.

## Synthetic scenarios

The invented Java 11-compatible fixture exercises a clean
commit, prior-marker conflict, another marker arriving
between preflight and publication, \`CREATE_NEW\`
refusal for orphan stages, deliberately interrupted
staging, marker force and hard-link publication,
before/after hash mismatches, strict history-move
refusal, committed-but-unacknowledged history,
preserving the marker after inspection, and a
**second independent Java process** reopening a
synthetic committed history after a deliberately
nonzero child exit.

A public Python structural gate inspects only this
invented Java fixture. It requires forced stage and
marker writes, the no-clobber hardlink, pre- and
post-publication hash verification, strict history
replacement, known-pre-replace-only rollback, and
no automatic final marker cleanup. Python tests
mutate the fixture to ensure regressions are
refused. Passing this gate **does not** verify
any recovered private Java source or JAR.

Hosted GitHub Actions exercises the public model
on Windows and Ubuntu with Python 3.11/3.13 and
JDK21 \`javac --release 11\`. Exact result is
determined by the corresponding CI run and must
not be assumed before it completes.

## Private-side work remains unverified

The intended owner-TEMP workspace for a future
private R415 candidate is:

\`R415-Private-Nonclobber-Delete-Intent-Producer\`

The private patch script was written but its execution
attempt received a remote-agent timeout with an
ambiguous completion state. **No private R415 compile
or source/class-delta receipt has been confirmed.**
Do not create a new private JAR, derive a SHA-256
from a previous milestone, launch a client, or
declare the private source patched until the
remote owner device is accessible for read-only
reconciliation.

A future validated private integration must reconcile
that workspace, verify the exact intended source/class
scope against R414 and SHA-pinned R381 reference,
check canonical Java string/newline serialization,
perform a full isolated JDK21 compile, run the
read-only private static audit and independent
negative controls, and remain unmerged.

## Safety limitations

No directory metadata durability or sudden
power-loss guarantee; no process-independent
writer lock; no authenticated intent marker;
no proof against external concurrent writes or
hostile tampering; no automatic recovery; no
safe marker cleanup; no v309 game runtime or
v312 compatibility acceptance; no actual Swing
latency benchmark or freeze-root-cause proof.

The synthetic model does not reproduce private
GSON behavior, actual history JSON, native
Windows file retention, all filesystem providers,
or real interleavings of the game's threads.

**R415 is public-only synthetic verification until
the private candidate can be independently
verified. Do not merge, launch, install, publish
or distribute a private game build.**
