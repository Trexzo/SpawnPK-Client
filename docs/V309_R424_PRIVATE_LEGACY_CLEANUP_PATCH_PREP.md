# R424 — SHA-pinned owner-private legacy cleanup patch preparation

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R423 draft PR #1219  
**Status:** DRAFT / UNMERGED, RELEASE CLOSED. **Actual owner-private source has NOT been modified or compiled by R424.**

## Purpose

R423 confirmed that the previous private `LootHistoryStore.deleteTree(File)` recursively uses `File.listFiles()`, which follows directory symlinks and can enumerate files outside the intended legacy cleanup path. R423's independent safer research model passed its final 4/4 hosted Windows/Ubuntu matrix, but was **not integrated into private source**.

Desktop Commander reached its monthly usage limit before R424. R424 therefore prepares a **restricted, reproducible source overlay** rather than pretending to install or compile a private fix.

## Owner-local patcher (opt-in, future execution only)

`tools/r424/prepare_private_legacy_cleanup_patch.py`

The patcher accepts an explicitly provided **isolated R421 source root**, the checked public helper file, and a **fresh direct child of the owner TEMP directory** named `R424-Private-Candidate-*`. It:

1. Requires exactly **1,277** parent Java sources and the source SHA-256 for R421 `LootHistoryStore.java`: `0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29`; refuses unrecognized, newer, symlinked, or already-patched source trees.
2. Requires the public companion `LootLegacyCleanupR424.java` SHA-256 `10b547561a7631315c5f44db118376c1a94f6a4cf259f7744f79af8453df18d7`.
3. Validates exact method and caller signatures for the old `r419DeleteStaleLeased()`, old recursively traversing `deleteTree(File)`, original stage fence, and seen-keys deletion. Any drift or unexpected callers **REFUSE**. The old recursive method and its obsolete Javadoc are removed in the overlay.
4. Stages a **copy** of the complete isolated source tree under a fresh TEMP destination. It changes exactly one existing source (`rs/plugins/loottracker/LootHistoryStore.java`) and adds exactly one public companion (`rs/plugins/loottracker/LootLegacyCleanupR424.java`), yielding **1,278** Java source files. The original private source tree is left unchanged.
5. Replaces legacy cleanup with a **complete no-follow preflight only**, invoked under the existing R419 writer lease and R411 unresolved-stage gate. The new private caller hardcodes `false` as the cleanup commit argument, so **NO retired files are automatically deleted** in the proposed R424 candidate.
6. Preserves the original Java source's LF or CRLF newline convention when constructing the overlay, and writes source **as bytes**, avoiding Windows `CRCRLF` corruption. Outputs a preparation receipt explicitly stating **NOT COMPILED** and **NOT RELEASE AUTHORIZED**.

**This script was NOT run on the owner's recovered private source** because remote access is paused. The tool does not rebuild a private JAR or launch the game even if it is run later.

## Independently authored no-follow helper

`tests/fixtures/r424/LootLegacyCleanupR424.java` is public-safe, Java 11-compatible source. It contains no recovered private bytes or game imports. It supports explicit `run(parent, admission, commit)` in two modes:

- **Preflight/dry-run** (`commit=false`): reject symlinks and unsupported entries, preserve journal evidence and histories, bound traversal by 16 levels / 4,096 entries / 64 MiB per file, and return `SCANNED`, `NOT_PRESENT`, `REFUSED`, or `INTERRUPTED`. The private overlay uses **only this mode**.
- **Synthetic commit mode** (`commit=true`): available only for independent test cases; performs complete preflight and rechecks each entry, ancestors, and admission callback before deletion. It reports `PARTIAL` if an interrupted/ambiguous deletion cannot be rolled back. **This is not enabled by the private patch.**

Both modes refuse execution on Swing's event thread. The method assumes its private caller already holds the R419 cooperative writer lease. It is **not** anchored against hostile ancestor path swapping, is not protection from foreign writers, and does not solve synchronous panel deletion or journal restart adoption.

## Public tests and evidence

Local offline verification on JDK21 with `javac --release 11`:

- **28/28** fabricated-private-source patcher tests passed. They check exact source signature and SHA admission, reject changed/ambiguous recursion, prevent repeated application, preserve unrelated methods, compile a generated fabricated Java store alongside the public helper, and verify a simulated private startup cannot delete its invented retired tree or keys.
- Independent Java 11 helper and harness compiled and passed **22 behavioral assertions** on Linux with invented TEMP files, including a non-destructive dry-run, synthetic explicit commit, unrelated/canonical history preservation, symlink and marker rejection, preinterrupted thread refusal, and EDT refusal. Symlink checks are optional where Windows privileges forbid their creation.
- The initial 24 test suite exposed a missing negative for CRLF byte preservation; after correction the expanded **28/28** suite passes.
- Hosted Windows/Ubuntu × Python 3.11/3.13 JDK21 matrix is a **public-only** test of the helper, fabricated store and patch tool; verify on final PR HEAD before claiming hosted PASS. Hosted CI does not include private source or client.

## Hosted cross-platform CI and line-ending correction

The initial hosted run failed two Windows SHA tests because Windows Git checkout rewrote the public Java helper's line endings from LF to CRLF. The patcher now accepts **only LF or CRLF**, normalizes the public helper to canonical LF **before verifying its pinned SHA**, refuses stray carriage returns, and writes the pinned canonical helper bytes to the private overlay. The **private R421 source SHA check remains exact on raw source bytes**; private source newlines are preserved during patching.

**Final verified dedicated public-only workflow:** `v309-r424-private-cleanup-patch-preparation`, run **43745863238**, **4/4 PASS** (Windows and Ubuntu × Python 3.11/3.13, JDK21). Each hosted job executes 28 fabricated patcher/negative tests and 5 helper tests (33 total); the Java helper's own nested acceptance performs at least 20 filesystem assertions per platform (22 on local Linux). Hosted success does **not** mean the private source overlay was executed or compiled.

## Remaining release blockers

**The actual R421 private `LootHistoryStore.java` has NOT been patched.** Source-only preparation is not runtime acceptance. No private Java11 compile/class-byte diff, no actual private store TEMP test after overlay, no real client or Swing event lifecycle, no R422 private multi-process rerun, no verified compatibility with installed v312, and no journal adoption or safe asynchronous confirmed-deletion receipt protocol. The R424 private overlay intentionally disables retirement cleanup rather than trying to perform potentially unsafe automatic deletions.

To proceed when owner device access resumes, apply this tool only to a fresh isolated R421 copy, verify its exact SHA receipt, compile all 1,278 Java sources against the pinned dependencies with `javac --release 11`, audit the complete class-byte delta, exercise the actual reconstructed store on fabricated TEMP histories, and separately test competing clients and Swing shutdown. Do not touch actual loot history or enable automatic deletion as part of that phase.

**Keep draft and unmerged. No production installation or release is authorized.**
