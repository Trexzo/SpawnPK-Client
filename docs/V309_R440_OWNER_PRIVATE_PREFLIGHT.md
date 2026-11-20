# R440 — Owner-private read-only acceptance preflight (mandatory source gate)

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R439 draft PR #1235  
**Status:** DRAFT / UNMERGED / OWNER-PRIVATE ACCEPTANCE NOT EXECUTED. No live SpawnPK client, actual loot history, private Java classes or deletion journals were touched for this PR.

## Why R440 matters

The old `tools/r425/owner_only_run_r425.ps1` calculated SHA256 for the two owner-private dependency JARs in the same invocation that passed those hashes to R425 and R432 as their expected pins. That can detect **mutations after the hash is measured**, but by itself it does **not** attest that the original files are the intended, previously approved dependency bytes. A replaced dependency would simply receive a new passing hash. That is the most important remaining preparation weakness before attempting a real private-source compilation.

## Changes

1. Add `tools/r440/read_only_private_acceptance_preflight.py`, a local-only **read-only** audit. It requires exact canonical owner-TEMP R421 source/class directory positions; refuses link, junction or special-file trees; reuses R425's original R421 Store source SHA and compiled class SHA, full **1,277 source / 1,394 class** checks, and the two **explicitly supplied** SHA256 reference values for `R239_filtered.jar` and `R218.jar`. It also checks public helper content with R424's SHA-pinned canonicalizer, checks public R422/R425 harness presence, runs only `java -version` and `javac -version` to require JDK21, and invokes the actual R424 patch-shape validator **in memory** on the original pinned Store source. It rehashes the baseline and dependencies before returning.
2. Update `tools/r425/owner_only_run_r425.ps1`: `-AuditOnly` executes just the read-only preflight, **without creating a candidate destination or compiling**. The existing explicit `-RunOwnerPrivateAcceptance` mode now runs the exact same preflight as a mandatory first stage, then R425 isolated overlay compile and R432 same-class cross-process acceptance only if it passes.
3. Both modes require `-ApprovedDependencyASha256` and `-ApprovedDependencyBSha256` with 64 lowercase hex characters, supplied separately from a previously trusted inventory, artifact or human-reviewed custody record. The script can compute **observed** hashes for comparison but may no longer treat those observed hashes as the trusted expected values. A mismatch, unapproved digest, source/class drift, malformed patch shape, unknown JDK, or nonisolated path refuses acceptance before staging.
4. The preflight emits only a **brief stdout JSON status**, not raw source, inventory, local paths, actual history content, or a file on disk. `python -B` suppresses Python bytecode cache writes during audit. Its pass receipt says **supplied reference hashes matched**; it cannot establish where the user supplied reference hashes came from. Confirm the reference hashes against a genuinely independent owner-approved baseline rather than calculating them immediately before invocation.
5. This does **not** integrate R427–R431 into the real private Store/Plugin. It does not generate a client JAR, launch a game, delete history, remove persistent R415/R417 intent/ack/stage markers, unblock writes, deploy, or authorize merge.

## Owner-side usage (not executed here)

Use PowerShell 5.1 with the repository checked out on the owner PC and the previously isolated R421 acceptance trees present. Replace the two placeholder hashes with values from a **separately reviewed known-good** R421 dependency inventory. Do not paste original Java files, private JARs, player data or credentials into GitHub.

```powershell
$entry = 'tools\r425\owner_only_run_r425.ps1'
$approvedA = '<64 lowercase hex from independently reviewed R239_filtered.jar baseline>'
$approvedB = '<64 lowercase hex from independently reviewed R218.jar baseline>'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $entry -AuditOnly -ApprovedDependencyASha256 $approvedA -ApprovedDependencyBSha256 $approvedB
```

**A successful audit is not permission to compile or release.** The separate opt-in `-RunOwnerPrivateAcceptance` path will still require the exact owner-private R425/R432 result, 39+ and 73+ actual Store assertions, 17 cross-JVM cases, full SHA inventories and a closed release gate. It must remain isolated to TEMP; never use installed/live source or player histories.

## Evidence and remaining blockers

A Windows/Ubuntu × Python 3.11/3.13 JDK21 GitHub matrix runs 12 **invented-data** preflight tests plus inherited public R432, R424, R426 and R433 suites. Tests cover matched and drifted supplied hashes, wrong class pins, wrong Java major, malformed cleanup shape, tampered helper, link refusal, no modifications to fabricated source/classes/dependencies and PowerShell audit-first ordering.

Hosted CI cannot access the real owner-private R421 tree. **R440 public CI is not actual owner-private preflight success**, and even a real preflight PASS is not the 1,278-source compiler acceptance. The previously quota-blocked remote Desktop Commander has not been retried. Real R425/R432 execution, production R427–R431 asynchronous delete adapter, Swing EDT responsiveness, plugin lifecycle, and v312 runtime/restart testing remain separate future gates.

Keep all stacked PRs draft/unmerged, and production release/write admission CLOSED.
