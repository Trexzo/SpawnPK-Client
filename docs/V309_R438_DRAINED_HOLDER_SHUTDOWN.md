# R438 — drain JVM pipes during held-owner shutdown

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R437 draft PR #1233  
**Status:** DRAFT / UNMERGED / public acceptance infrastructure only.

## Verified source-level liveness defect

The R422 cross-JVM acceptance runner starts a synthetic held owner with both stdout and stderr pipes captured. After reading its first `ACQUIRED` record, it sends an input newline to request shutdown, then called `holder.wait(timeout=10)` **before** reading stdout and without draining stderr at all. A JVM can write enough output to fill an OS pipe and block while exiting. Waiting for its exit before draining either pipe can create a classic child-parent pipe deadlock. R434's startup timeout and R437's exact ownership protocol do not remove this shutdown-specific failure.

This is a public harness design defect, **not evidence of a real client deadlock**.

## R438 implementation

- Add `release_holder_and_collect(holder, timeout=10)`: write one newline on the synthetic holder's stdin, flush and close stdin, then use `Popen.communicate(timeout=10)` to drain stdout and stderr concurrently before accepting termination. Preserve the exact `RELEASED` response from R435 and explicit `holder.returncode == 0` check; neither may be inferred from extra output or a partial exit.
- On any timeout or earlier test refusal, the existing holder `finally` still checks for a live process, kills it and calls `communicate(timeout=5)` to drain/reap. Stream handles are closed. This is a synthetic subprocess cleanup only: it does not release or take over a real Store writer lease.
- Update inherited R434/R437 structural tests to assert the safer communication order instead of the previous `wait`-before-drain pattern.
- No changes to original private Java source/class SHA pins, R422's 17 named receipt checks and 73 actual Store assertions, R425's 39 Store assertions, R432 acceptance chaining, R415/R417 intent/ack markers, or write fences.

## Executable evidence scope

Nine public regression methods use disposable Python child processes with real OS pipes for a normal owner close, a **700 KB stderr burst** large enough to fill standard pipe buffers, invalid success output, nonzero exit, release timeout/killed child, argument checks, stable 17-case receipt labels, and confirmation that the actual runner uses concurrent pipe draining. A Windows/Ubuntu × Python 3.11/3.13 workflow also runs inherited R437–R432 public suites. The independent R422 public test workflow is triggered by the runner change.

Hosted CI does **not** include owner-private R421 bytecode, the installed v312 client or real player history. Even a green run proves only the synthetic harness's lifecycle. No merge, client launch, deletion, journal cleanup, history-write admission or deployment is authorized. The owner-only R424→R425→R432 full private compile and actual class checks, R427–R431 real async Store/Plugin adapter, and Swing lifecycle/restart acceptance remain outstanding.
