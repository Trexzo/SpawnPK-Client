# R436 — exact R422/R425 Java self-test receipt parsing

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R435 draft PR #1231  
**Status:** DRAFT / UNMERGED, public gate hardening only.

## Evidence problem

Both R422 and R425 had a `re.search` for their final Java harness success token and a decimal assertion count. Such a search could accept a misleading string like `NOT_R422_ACTUAL_PRIVATE_STORE_PASS assertions=73`, or the same phrase embedded in unrelated failure output, provided the child process exited zero. The R432 private gate trusts these upstream counts, so success must require an unambiguous complete harness receipt.

## Implemented gate

- `parse_r422_selftest_assertions` requires exactly `R422_ACTUAL_PRIVATE_STORE_PASS assertions=N` followed by the complete terminal newline.
- `parse_r425_selftest_assertions` requires exactly `R425_ACTUAL_PATCHED_PRIVATE_STORE_PASS assertions=N` followed by its newline.
- Each parser permits precisely one explicitly known optional warning line **before** the receipt (R422 or R425 `OPTIONAL_SYMLINK_UNAVAILABLE`). The warning only arises when a synthetic symlink test is unsupported on the machine.
- Each parser accepts LF or CRLF consistently across the output; refuses extra stdout, injected prefixes/negations, duplicate receipts, missing newline, mixed line endings, leading zeros, non-ASCII digits and counts with more than six digits. Stderr is never an acceptance source.
- Callers retain their successful child exit-code checks and minimum assertion requirements (**73** for R422, **39** for R425). The exact parsed count, not a searched substring, is written to the owner-only receipt.
- R422's 17 required cross-process case labels, R435 exact ownership tokens, and R432 private source/class SHA and release fences remain unchanged. There is no adoption of the speculative R429 journal.

## Test coverage

Eleven focused Python tests cover valid LF/CRLF receipts, optional symlink warning, deceptive status text, warning order, malformed counts, minimum thresholds, actual Java harness producer source, exact R422/R425 acceptance wiring, and real synthetic Python child processes. Windows/Ubuntu × Python 3.11/3.13 CI also executes inherited R435/R434/R433/R432 and the R426 fabricated full Java build.

Hosted CI never contains the private R421 source/class, installed client JAR or real loot history. A green workflow validates the **public test gates**, not the owner-private compile, plugin, or live Swing acceptance.

## Outstanding owner-private gates

Require the R424 1,278-source overlay compile, actual R425 class acceptance, R432 actual-private same-class 17 process checks and 73+ assertions, real R427–R431 LootHistoryStore/LootTrackerPlugin adapter, and physical v312 UI shutdown/restart tests. Preserve R415/R417 intent/ack evidence and write refusals; no deletions, automatic cleanup, merge, release or deployment are authorized.
