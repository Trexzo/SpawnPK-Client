# R433 — source-compatible R424 cleanup guard and real receipt producer audit

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R432 draft PR #1228  
**Status:** DRAFT / UNMERGED; public test coverage only, owner-private release gate CLOSED.

## R433 finding

R432's cross-process gate expects 17 exact check labels from the R422 process runner, a specific source/class inventory and exact receipt fields from R425. R433 reviewed the checked-in **actual public runner code**, not fabricated sample receipts, and confirmed the 17 names and expected R425 receipt structure align.

However, R424's private overlay generator used an **unverified exact private enum reference**:

`r411StageState() == R411StageState.CLEAR`

The R424 fabricated private-source stub previously defined this enum itself. That test setup could make a fabricated Java 11 build pass while an actual owner-private `LootHistoryStore` compiled from the pinned R421 source might not define that enum. This is a true source-compatibility risk. The *existing R421 cleanup call* was already evidenced to invoke the boolean `r411RefuseUnresolvedStage("legacy cleanup")`, so its return type and existence are grounded much more strongly.

## Implemented change

`tools/r424/prepare_private_legacy_cleanup_patch.py` now generates:

`() -> !r411RefuseUnresolvedStage("legacy cleanup")`

for the public helper's repeated **inspection-only** admission callback. This reuses the known existing boolean method, checks the same unresolved-stage gate again, and removes the speculative `R411StageState` type and `r411StageState()` dependency from the replacement. R424's existing direct initial `if (r411RefuseUnresolvedStage("legacy cleanup")) return;` is retained.

**The following are unchanged:**

- The private R421 `LootHistoryStore.java` raw SHA256 pin: `0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29`.
- The R421 compiled Store.class exact SHA256 pin: `65272371272fdcf9142095880a042aa007a9a088f93c969a57878188fae37a09`.
- The public `LootLegacyCleanupR424.java` canonical SHA256 pin: `10b547561a7631315c5f44db118376c1a94f6a4cf259f7744f79af8453df18d7`.
- The exact allowed source/class delta and 1,277→1,278 source and 1,394→1,399 compiled class expectations.
- **`commit=false` remains hardcoded. No legacy tree or seen-keys deletion can be triggered from the proposed private overlay.** R411/R415–R417 journal evidence remains untouched. No client JAR is built or installed.
- No SHA override, skip mode, alternate unpinned private tree, automatic cleanup or release authorization was added.

## Stronger, actual compilation-facing tests

`tests/test_v309_r424_patch_gate.py` now deliberately removes **both** `R411StageState` and `r411StageState()` from its independently invented `LootHistoryStore` facade, then verifies the patched Java compiles with `javac --release 11`, runs the fabricated no-delete acceptance, and uses only the pinned boolean guard. The test also verifies that an unresolved guard can return true and that the generated callback still negates that result rather than granting unconditional admission.

The more comprehensive `tests/test_v309_r426_full_mock_pipeline.py` no longer defines the unverified enum either. It retains an unrelated nested metadata class to preserve its baseline exact class count (4), still executes R424 patch → actual `javac --release 11` full mock build → exact 4→9 class delta → R425 synthetic actual-Store acceptance, and uses an invented direct boolean journal-marker check.

`tests/test_v309_r433_real_producer_contract.py` adds **six AST/code-grounded assertions** (not mocks) against the existing R422 and R425 **actual public Python code**:

1. Parse all static R422 `passed("name", ...)` calls in its real `main()` and require exactly the 17 distinct names in R432's gate, without a missing or invented check.
2. Parse R425's **actual generated final receipt keys** and all false safety flags; require these match R432's consumer.
3. Verify the real R425 Java-harness return payload has the exact status and assertion counter names required by R432.
4. Verify R422's actual output payload contains the exact status, SHA, assertions, case list and three false safety flags.
5. Assert original private source/class SHA pins remain unchanged, helper dry-run remains hardcoded, and no stage enum is introduced.
6. Cross-check exact R422 producer status/SHA field names against R432's source consumer.

## Hosted CI and remaining blocker

A dedicated Windows/Ubuntu × Python 3.11/3.13 / JDK21 matrix runs the source patch/JDK11 tests, end-to-end fabricated build, R432 safety chain and the R433 producer/consumer contract audit. The matrix verifies **public code** and does not have owner-private R421 source/class bytes.

**Until the final head's GitHub CI succeeds, do not claim R433 is validated.**

Crucially, because Desktop Commander previously enforced a monthly use limit and explicitly instructed not to retry, this replacement has **not** been applied to, compiled against or run with the owner's actual R421 private Java tree. The source-exact old method shape and class changes still require the real R425/R432 owner-private test chain. There is no verified R427–R431 real asynchronous deletion adapter, persisted acknowledgment or live Swing/plugin lifecycle acceptance. No actual history files, journal markers, original client or installed v312 JAR changed in R433.

**Status:** keep PR DRAFT/UNMERGED; production release remains CLOSED.
