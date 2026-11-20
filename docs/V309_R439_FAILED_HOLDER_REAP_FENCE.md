# R439 — Join failed holder reader before safe synthetic process reaping

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R438 draft PR #1234  
**Status:** DRAFT / UNMERGED / NOT DEPLOYED. Public acceptance infrastructure only.

## Real issue in the checked-in R422 acceptance runner

R434 established a background thread reading the first line of a held JVM's stdout, with a deadline. R438 later introduced a `communicate()`-based child cleanup on failures. When a holder silently hangs or only emits part of an unterminated line, the original first-line reader can remain blocked on the same `TextIOWrapper` as the outer cleanup's `communicate()`. Concurrent reading and closing of the same stream can deadlock or lose output, and is not a valid basis for a passing R432 private acceptance receipt.

This is **public acceptance-harness** code; no claim that real SpawnPK hangs has been proven.

## Implemented correction

- `read_holder_announcement()` retains the R434 ten-second deadline, the R437 64-character read cap and exact complete `ACQUIRED`/`REFUSED_OWNER`/`REFUSED_PREPARE` tokens.
- On deadline, it explicitly kills **only the disposable synthetic holder child** (tolerating an exit race), then joins the blocked reader before allowing the outer cleanup to drain that pipe. A reader that cannot be joined refuses acceptance; it cannot issue a valid owner receipt. If a pipe is inherited by a descendant and the reader remains alive even after the direct child exits, cleanup does **not** concurrently read or close the reader-owned stdout stream; it leaves the result unconfirmed rather than deadlocking on that pipe.
- The successful or refused announcement path also joins the completed reader; all the existing exact protocol and exit-code checks stay mandatory.
- `reap_synthetic_holder()` centralizes fail-closed finalization for a synthetic child after normal release, failed contender check, malformed announcement or timeout. It tolerates a process disappearing between poll and kill, uses `communicate(timeout=5)` to drain both pipes and reap, and closes local streams. A reaping timeout emits `R422_HOLDER_REAP_UNCONFIRMED` rather than falsely claiming successful shutdown.
- The R422 `finally` uses this helper. Inherited R434/R437/R438 static assertions now inspect it rather than assuming earlier inline cleanup implementation.
- Existing R422 17 case labels, at least 73 Store assertions, R425 39-assertion threshold, R432 same-class SHA acceptance, R415/R417 persistent journal and post-delete write refusal remain unchanged. No second R429 ledger is adopted.

## Evidence plan

Fifteen focused synthetic-process and mock regressions cover already-released child reaping, initial stdout silence, partial lines, stderr saturation before acquisition, malformed output, failure between acquisition and release, release timeout, early EOF, concurrent exit during kill, unreapable child refusal, and the exact R432 receipt contract. CI is Windows/Ubuntu × Python 3.11/3.13 with JDK21 and inherited R438–R432 suites. **Do not call the final commit verified until GitHub checks finish.**

## Owner-private integration — next meaningful gate

The real recovered private R421 source/class and dependency JARs are not present in GitHub CI. The owner-only SHA-pinned R424/R425/R432 scripts must run on the isolated owner machine against the **actual** R421 1,277-source baseline and accept the 1,278-source candidate, with R425's 39+ true private Store assertions and R432's 73+ actual Store assertions / 17 cross-process cases against the exact newly compiled class SHA.

Only after that exact private compile/acceptance succeeds should a separately reviewed, shutdown-aware R427–R431 async adapter be proposed for `LootHistoryStore` and `LootTrackerPlugin`. Real Swing callback responsiveness, owner-close ordering, restart intent/ack interpretation and v312 integration still need physical acceptance. Public fixture passes are not evidence of real client integration. Never clear R415–R417 intent, ack, stage or lock files, enable writes, auto-merge, install a JAR, or deploy on the strength of R439.
