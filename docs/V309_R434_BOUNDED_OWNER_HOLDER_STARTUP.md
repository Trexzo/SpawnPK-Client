# R434 — bounded cross-process holder startup (public-safe)

**Repository:** Trexzo/SpawnPK-Client  
**Base:** R433 draft PR #1229  
**Status:** DRAFT / UNMERGED. No private-client integration, deployment, or history write authorization.

## Reproduced source defect

In R422's existing owner-private cross-JVM acceptance runner, the first owner process was started with an OS stdout pipe and the caller executed `holder.stdout.readline()` before performing the competing-process check. This was **unbounded**: a JVM that starts but stalls before printing `ACQUIRED\n` can cause the Python harness to wait indefinitely. The R432 outer subprocess has a 180-second limit, but killing its direct Python process does not guarantee cleanup of a descendant JVM that the Python harness never reached its `finally` block to reap.

This is a harness liveness/cleanup gap, **not** evidence of actual deadlock in the client.

## R434 change

- Adds `read_holder_announcement(holder, timeout=10.0)` in R422. A daemon reader thread handles the potentially blocking pipe read; a queue get applies a cross-platform deadline, avoiding use of Unix-only `select` on anonymous Windows pipes.
- Raises an explicit refusal on **no line**, premature EOF, failed pipe read, or invalid deadline. It does not invent `ACQUIRED`; R422's existing exact `line == "ACQUIRED"` test remains mandatory.
- The existing holder `try/finally` still kills/reaps an unreleased child, then closes stdin/stdout/stderr, including on deadline refusal. It does not force release of an owner lease or clean markers.
- Leaves the R422 17 named case labels, 73-assertion requirement, SHA identity fields, TEMP-only scratch roots and R432 closed release gate untouched.
- New R434 synthetic real-process tests exercise prompt announcement, indefinite silence, bytes without newline, early EOF, explicit ownership refusal, invalid arguments, and static confirmation that the actual R422 call path remains inside its child-process cleanup `finally`.
- Windows/Ubuntu and Python 3.11/3.13 CI exercises the eight tests plus inherited R433 and R432 public contracts. Hosted CI **does not** access real owner-private classes, history, or JARs.

## Remaining gates

The R424 overlay still requires compilation against the SHA-pinned private R421 Java source. The R425/R432 actual-private chain (39+ actual Store assertions, 73+ actual Store assertions, and 17 cross-process checks), the R427–R431 adapter into real LootHistoryStore/LootTrackerPlugin, and physical Swing shutdown/restart and v312 acceptance remain unverified. R434 is **not** a green light to delete evidence, remove persistent intent markers, reopen writes, merge PRs, or deploy a client.
