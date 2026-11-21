# R459 — Consolidate offline SpawnPK client inspection into one evidence-classfile read per pass

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R458 draft PR #1255, 4/4 public Windows/Ubuntu CI passed on `ccc442ce`  
**Status:** DRAFT / UNMERGED / OWNER-PRIVATE ONLY / NO DEPLOYMENT

## Bottleneck and concrete optimization

The R447→R458 owner audit pipeline is intentionally conservative but deeply recursive: later `inspect()` functions invoke the previous audit and then independently re-observe the same R421 tree, re-read compiled classes, revisit dependency ZIPs and reparse member references. Its repeated full-file reads can be expensive on a real source tree. R458 does not itself provide a compact, integrated view of its R449–R457 findings.

R459 introduces **a separate, comparison-ready consolidated inspection path** rather than silently rewriting or weakening existing evidence gates:

1. `r446.observe()` admits the exact owner-isolated TEMP roots with nofollowing checks; verifies all **1,277 Java sources / 1,394 compiled Java11 classes**, exact `LootHistoryStore.java` and `.class` SHA pins, and the current SHA of both dependency JARs. These are *current-state* fingerprints only, not independently certified historical R421 custody.
2. Read the pinned v309 JAR once and validate exact SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, **10,502 original classes / 419 resources**, ZIP central-directory safety, and SHA-guarded preferred R239 and alternate R218 archives.
3. During the **evidence pass**, read each rebuilt classfile **exactly once**, independently verify its current bytes against the first R446 observation, then reuse those immutable in-memory bytes across **already-tested** R453 class and member metadata, R458 dynamic/bootstrap analysis, and R450's Code/Signature scanner. The R450 `Code` observer fans out to R451 straight-line and R452 forward CFG resource attribution and the R456 direct JVM instruction collector; this reuses the same parsed method Code rather than reopening files.
4. Reuse the resulting class metadata and selected preferred dependency JAR bytes to perform R453 direct declarations, R454 inheritance, R455 selected dependencies, R456 static/instance opcode classification, R457 invocation constraints and R458 bootstrap/MethodHandle summaries **without calling the nested legacy owner audits again**.
5. Enforce cross-parser equality for exact `invokedynamic` instruction counts (R456 vs R458) and CP/member counts (R453 vs R454) and whole class totals. Inconsistent parsers fail closed, rather than generating a passing aggregate from contradictory evidence.
6. A second **full `r446.observe()`** rehashes all current source/class/dependency files independently after the evidence pass. The original pinned v309 JAR is also re-read and SHA-verified, catching modifications during analysis.

**Important exact interpretation:** “One read” means one read **per compiled class within the evidence-parsing pass**, not a single read during the whole audit. The mandatory initial and final R446 inventories each read and hash every class, yielding **three total compiled-class reads** in the normal unchanged R459 path. This is deliberate; we do not claim immutable disk files, allow persistent caching, or bypass the second custody scan.

R459 reports `classfile_evidence_pass_reads`, aggregate bytes read, two `full_R446_inventory_observations` and `recursive_legacy_owner_audits_invoked=0`. Its purpose is lower repeated disk I/O, less duplicate parsing orchestration, simpler audit results and clearer next-step reconstruction leads. **No numerical real-owner speedup is claimed until the owner machine is available for a measured comparison.**

The old R447–R458 CLI behaviors are unchanged and remain available for independent comparisons or investigation. R459 itself is an **unapproved alternative**, not automatic promotion of a previously approved recovery workflow.

## Output and owner safety

Normal output is aggregate-only: original/rebuilt inventory counts; direct and inherited member-reference counts; preferred dependency declaration signals; actual JVM opcode and static/instance warnings; invocation-rule findings; dynamic/bootstrap handle counts; and candidate resource arguments from R450/R451/R452. It prints **no private class, method, source, resource path or original bytes** and does not create a report by default.

The optional `--save-private-unapproved-worklist` flag requires two **complete identical R459 analyses** including the initial/final inventory SHA observations and exact full source/class/dependency identity. A single exclusive owner OS TEMP folder then contains `R459-UNAPPROVED-RECONSTRUCTION-WORKLIST.json`. This is an owner-only name/descriptor/PC evidence list, not a copy of source/class/JAR bytes. Existing reports are never overwritten.

To run on the authorized owner computer (when reachable):

```powershell
python -B tools\r459\audit_consolidated_inspection.py --original-v309-jar '<owner-local exact original v309 client.jar>'
```

To opt into a private quarantined candidate worklist append `--save-private-unapproved-worklist`. The optional `--resource-companion-root` only checks an **existing** private companion directory for exact original resource byte matches; it does not install or package assets.

The **historical independently approved** R421 full source/class manifest required by R442/R440/R425/R432 remains **missing**. R459 **does not** reconstruct, certify or fabricate such history. No compile authorization, client replacement, remote access to user histories, deletion-intent cleanup, R415/R417 write fence bypass, R440 approval or runtime startup is attempted.

## Validation and remaining work

The public test suite uses **25 fabricated owner trees and classfiles**, tests one evidence-read per compiled class alongside the two mandatory complete R446 observations, parity on common R458 synthetic dynamic counts, nonrecursive source-scanning, exact original and Store pins, per-class SHA drift, source mutations between private scans, cross-parser count disagreement, no-write defaults, new/private-only output and no historical approval. Inherited R458–R445, R442 and R426 synthetic regressions also run on Windows/Ubuntu × Python 3.11/3.13.

No actual private R421 source/JAR/assets, no installed client, no production player history or persistence journals are present in public GitHub CI. Owner desktop `DESKTOP-LTXXO4K` remained offline at R459 intake. Full readable source parity, compile + package, v312 patch acceptance, UI/login/gameplay, FPS and actual cold/warm benchmark data are **not verified**.

**R459 must remain draft/unmerged. No private data export to public GitHub, client installation, destructive cleanup, production write unlock or release authorized.**
