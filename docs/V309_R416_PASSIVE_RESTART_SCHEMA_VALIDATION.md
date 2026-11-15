# R416 — passive committed-history schema verification (phase A)

**Repository:** Trexzo/SpawnPK-Client
**Stacked on:** R415 draft PR #1211
**Status:** DRAFT / UNMERGED. Not marker acknowledgment, cleanup or release.

## Why R415 does not finish recovery

R415 publishes a no-clobber v1 intent marker before replacing history. R414 can classify its before/after hashes, but a matching SHA-256 does not validate JSON schema or justify automatic adoption. A changing disk image, staging file or foreign writer can invalidate observations.

## Owner-private isolated source candidate

A fresh copy of the private R415 source tree was created under the owner's Windows TEMP directory. Exactly one private Java source changed: rs/plugins/loottracker/LootHistoryStore.java.

The newly added package-private r416InspectRestartCandidate() is **read-only and currently dormant**:

1. Only examine the R414 COMMITTED_BEFORE_ACK state; refuse conflicting intent evidence.
2. Reject any unresolved history .tmp file, symlink, nonregular, empty or oversized source.
3. Read up to 64 MiB with NOFOLLOW_LINKS and verify metadata and digest consistency.
4. Parse the existing version-1 Document, RecordDto and ItemDto structures, refusing missing fields, unknown types, null items, excess items, negative item quantities and prices.
5. Serialize through the same Gson instance into a digest-only sink; require the exact original canonical SHA-256 rather than trusting permissive JSON parsing.
6. Revalidate the history digest and marker state after parsing.
7. Return COMMITTED_SCHEMA_VALIDATED_NO_ADOPTION as observation only. Never delete markers, restore the UI, or unblock writes.

The method is not invoked on the Swing EDT and is not wired into startup. No private Java, JAR, player history, credentials or account data is uploaded to GitHub.

## Verification on owner's Windows machine

- JDK 21 javac --release 11 compilation: 1,277 private Java source files -> 1,393 class files, exit 0.
- Exact source delta versus R415: one changed source, LootHistoryStore.java.
- Exact class-byte inventory versus R415: one changed existing LootHistoryStore.class plus exactly one new nested LootHistoryStore$R416RestartValidation.class, with no removals or unrelated byte changes.
- No original client executed and no live v312 files, history, caches or client packages modified.
- Public independent synthetic Python tests: 40 invented real-TEMP scenarios, including malformed markers, nonexistent and staged files, canonical/noncanonical JSON, schema rejection, digest mismatch and symlink refusal. These do not execute recovered Java classes or prove full runtime equivalence.

## Explicit remaining blockers

This is NOT a completed restart recovery or acknowledgment protocol. No marker unlink, cross-process writer lock, authenticated marker, directory fsync/power-loss proof, validated UI restoration, or real-client runtime test exists. R415 confirmed deletes still synchronously block the Swing event thread and quarantine subsequent writes. The read-only validator may consume memory proportional to the 64-MiB maximum, and its responsiveness has not been benchmarked.

Keep draft and unmerged; no private source deployment, live game execution, automatic marker cleanup, client release or distribution authorized.

**Next:** isolated restart adoption/acknowledgment protocol tests, followed by external-writer fencing and EDT-latency verification before activation.
