# R426 — full mock pipeline + build-input continuity gate

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R425 draft PR #1221  
**Status:** DRAFT / UNMERGED — private-client release gate CLOSED.

## Reason for R426

The R425 owner-only compiler protects initial source/class identities with exact SHA256 pins, then proposes applying R424's inspection-only legacy cleanup patch, compiling 1,278 Java files and running actual-store TEMP tests. However, it did not re-check **all** source bytes or both dependency JARs after its long compilation/runtime-acceptance stages. A mutated source or changed dependency could therefore slip through as long as the final class set matched a small shape contract. The compiled class scope was also only compared by *names of changed classes* rather than against an immutable post-compile byte snapshot.

R426 improves input continuity with full-tree rehashing, while retaining the same real R421 source/class digest pins, per-JAR supplied digest checks and "no live data/no deployment" policy.

## Changes to the R425 owner runner on the R426 branch

`tools/r425/compile_and_accept_private_overlay.py` now includes `verify_unchanged_build_inputs(...)` and checks:

- The entire original **1,277-source SHA inventory** remains unchanged.
- The entire original **1,394-class SHA inventory** remains unchanged.
- The newly prepared candidate **1,278-source SHA inventory** remains unchanged.
- Both independently supplied JAR SHA256 values still match after copy, after Java compilation and after actual-class acceptance.
- Compiled class bytes are snapped in a complete SHA inventory **immediately after javac** and compared again after the actual Java harness and before issuing a final acceptance receipt. A class rewrite with the same name now fails.
- The final receipt is issued only after all these continuity gates succeed. A mismatch fails closed with a specific R426 refusal code. This is an ordinary filesystem drift detector, **not** protection from a malicious actor replacing files between checks.

The actual private R421 baseline hash pins remain exactly the same, and R424's private patch still hard-codes `commit=false` for no-follow legacy cleanup preflight. No policy enables deletion or journal acknowledgment.

## A genuine end-to-end simulated pipeline

`tests/test_v309_r426_full_mock_pipeline.py` creates its own invented **two-source mini-client** in a synthetic, named R421-like TEMP workspace:

- It compiles the original fabricated `LootHistoryStore` and an unrelated Java class under JDK21 `javac --release 11`, building a miniature baseline containing four classes.
- It creates two empty synthetic dependency JARs and records their SHA256 digests.
- **Only within this test process**, `unittest.mock.patch` replaces the source/class SHA/count expectations with fixture-specific values. The actual owner-only command-line runner retains the original pinned R421 production values and exposes no bypass switch.
- It invokes the **real R425 `run()` orchestration**, including the real R424 source patcher, source inventory gate, full Java 11 compilation, helper class inventory verification, and the real R425 public acceptance harness loaded against the fabricated compiled store.
- It demands precisely **2→3 sources**, **4→9 classes**, one changed existing `LootHistoryStore.class`, five added R424 helper classes, and successful Java TEMP runtime acceptance while legacy files and deletion evidence are preserved.
- Further negative tests change either dependency JAR, a baseline Java source, baseline class or candidate source after hashing. Each must refuse with its corresponding R426 drift reason, without touching any real files.
- The output is an automatically cleaned fabricated TEMP folder. Nothing from the actual owner-private recovered client is used in these public tests.

**This corrects an important limitation of R425:** R425's hosted tests checked individual components but never ran the complete compiler and acceptance orchestration in one call. R426's fabricated end-to-end test now exercises that whole call path. It does **not** assert actual R421 binary compatibility, game startup, or live-player history safety.

## Hosted validation

Dedicated `v309-r426-full-pipeline-input-integrity` workflow runs on Windows/Ubuntu × Python 3.11/3.13 with Temurin JDK21. Always check the **final PR head** before claiming hosted PASS; earlier commits in the same draft may be queued or fail.

## Outstanding restrictions

Remote Desktop Commander remains quota-paused; it explicitly instructed not to retry or reconnect. No owner-private source, classes or client JAR have been modified, compiled or launched in R426. The R425 private compilation and R422 private cross-process retest remain unexecuted. R424 helper auto-deletion stays disabled. The real Swing `LootTrackerPlugin` lifecycle, confirmed-deletion EDT blocking, power-loss durability, hostile lock/path replacement and safe journal reconciliation remain outside the scope of this synthetic test.

**No merge, release, real-history access or deployment authorized.**
