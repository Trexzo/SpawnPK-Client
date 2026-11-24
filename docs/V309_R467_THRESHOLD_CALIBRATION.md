# R467 — calibrate R464 hierarchy cache activation threshold

Parent: R466 draft PR #1267, SHA 1f606a9e9914dd48a93b0caba5ae3a7e8de684fb.
Status: DRAFT / UNMERGED / PUBLIC SYNTHETIC INPUTS ONLY.

## Reason

R466 introduced a 16-distinct-target threshold. Synthetic CI measured
benefits from forced sharing with only 8 overlapping member references,
which the existing selector skips. It also showed that enabling the cache
without any overlap can increase overhead. A threshold needs calibration,
not an unsupported global-performance claim.

## R467 proposal

- Keep R466's default threshold of 16 untouched, including its prior
  regression tests and opt-in inspector.
- Supply a separate R467 SHA-gated inspector using an *opt-in provisional*
  8-distinct-target selector. All of R459's source/class/dependency SHA
  gates, source/class budgets, exact pinned original v309 archive and final
  inventory recheck remain in place.
- No cache if fewer than 8 exact member targets match; no opcode sites,
  malformed hints, or bounded-probe refusal still skip caching.
- Do not merge or promote 8 as a production threshold until the private
  owner current-state input is independently approved and benchmarked.

## Measurement

R467's in-memory benchmark sweeps these synthetic cases:

  Overlap owner/signature pairs:
    (1,1), (2,1), (4,1), (8,1), (12,1), (16,1), (24,1),
    (32,1), (8,8), (24,8)
  Negative control:
    (24,8) with zero modeled opcode sites.

All four modes use the **same** fabricated R453 class/member inputs:
independent R455/R456, forced R464 cache, adaptive threshold 8, and
R466 default threshold 16. Counters do not assume elapsed time will
improve. For each case, every complete public/private R455 and R456 output
must agree exactly. Time and tracemalloc peak allocations are recorded
using counterbalanced pairs; selector time is **included** in the adaptive
totals and separately microbenchmarked (median of 32 calls) to isolate
gate overhead.

No one synthetic threshold is established as universally optimal: results
depend on topology, signature reuse, implementation costs, interpreter,
CPU scheduling and workload. Real original-client completeness, source
inventory and gameplay performance cannot be inferred from this test.

R467 also checks the SHA-gated R459 fabricated owner fixture with exact
R459/R466/R467 public/private output parity and inherited
R466/R465/R464/R463/R462/R461/R460/R459/R456/R455/R454/R442 regressions
across Windows/Ubuntu, Python 3.11/3.13.

Run public synthetic sweep (no game inputs required):

    python -B tools/r467/benchmark_threshold_sweep.py --pairs 2

The benchmark only creates in-process fabricated structures; does not
open client JARs, private source trees, owner path, production history,
deletion journals, network sockets, or live game processes. It prints
aggregate-only JSON; does not export private names, hashes, source or JAR
bytes. Existing R415/R417 persistence fences and R421 historical custody
approval remain unchanged/unapproved.

No release, merge, compilation, runtime launch, production optimization
claim, or full reconstruction acceptance is authorized.
