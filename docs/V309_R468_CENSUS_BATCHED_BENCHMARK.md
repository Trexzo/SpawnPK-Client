# R468 — complete overlap census + reliable small-workload timing

Parent: R467 draft PR #1268, exact SHA 103ba5c3dcc5d36dea2a4fee7a21654be51f520b.
Status: DRAFT / UNMERGED / NO LIVE CLIENT EXECUTION.

## What R467 did and did not establish

R467's synthetic 8- and 12-reference cases favored the provisional cache
activation threshold 8 over the earlier threshold 16. Very small 1-reference
Windows cases showed unstable, implausibly large ratios; two paired
single-invocation traces were insufficient for a reliable threshold decision.
R467's Recovery CI and PR-targeted checks are now fully green, but that does
not establish a private owner-client performance improvement.

Two independent R468 additions address these limitations.

## 1. Complete read-only member-reference overlap census

tools/r468/overlap_census.py enumerates, from the **exact in-memory**
R453 and R456 records admitted by the existing R459 coordinator:

- Number of rebuilt class records and selected dependency records
- All R456 field/method opcode sites and distinct Member targets
- Distinct opcode targets with owners present in the combined class graph,
  excluding platform namespaces as R466 does
- Rebuilt-class constant-pool member-reference occurrences and uniques
- Exact DISTINCT intersection of both collections (owner, member, descriptor,
  field/method/interface kind), corresponding opcode-site occurrences, and
  count of distinct target owners
- Only numeric/boolean decisions for overlap thresholds 2/4/8/16

Unlike the early-exit R466 selector, the census scans *all* admitted
rebuilt references and refuses if its bounded limits prevent a complete
answer. It also separately calls the original threshold selector and
refuses any inconsistency when both complete checks are available.

Nothing in the output contains a raw Member, owner name, Java descriptor,
class/source path, bytecode, private worklist, dependency bytes, JAR data,
per-file hash, player history or production persistence record. Class data
and private evidence never leave the process.

tools/r468/audit_owner_overlap.py is **opt-in**, and invokes the existing
R459 SHA-gated audit with a transient selector callback. The callback
captures exactly one complete census, but no output is emitted until the
normal final complete R446 source/class/dependency SHA observation and
second exact-pinned original-v309-JAR read have succeeded. R459 retains its
original single-evidence-read path, independent R454 graph, distinct R455
and R456 semantic validation, exact source/class counts, bounded nofollow
reader and cross-parser parity.

A standalone private owner can run, READ ONLY:

    python -B tools/r468/audit_owner_overlap.py --original-v309-jar "<exact pinned owner-local v309 client.jar>"

This produces a **numeric aggregate-only JSON receipt on stdout** or a
redacted refusal, and creates no output files. The R467 default threshold 8
is used for the optional shared-cache admission; historical R421 custody
approval and source completeness are *not* inferred from a current-state
SHA inventory. No owner file is present in public GitHub CI, so R468's
real private-client overlap count is **still unknown** pending an
authorized actual owner-local run.

## 2. Replicated-batch microbenchmarks for very small workloads

tools/r468/benchmark_batched_thresholds.py works entirely with generated,
in-memory R453 class trees, never a real source/JAR/archive. It repeats
R455 + R456 complete analyses in each timed batch, prewarms every mode,
and alternates the order on consecutive trials. It compares:

  independent / forced cache / exact threshold 2 / 4 / 8 / 16

Cases include 1, 2, 4, 8, 12 and 16 unique synthetic overlaps, plus a
24-owner no-opcode negative control. Default five paired trials per case,
eight complete analyzer invocations in each timed sample. It reports
wall and CPU medians, median absolute deviations, min/max spread and
within-pair speedup ratios. On Windows the CPU process timer may be too
coarse for sub-tick batches and legitimately report zero CPU elapsed;
this is kept as a resolution-limited observation, not mistaken for a
failed run or a claimed zero-cost computation. Positive wall time and
complete evidence parity remain hard requirements. Tracemalloc is intentionally **disabled for
timing** in this pass, unlike earlier R467 runs, to reduce intrusive
measurement noise. Selector overhead IS included in every adaptive mode.

Every output includes a separate strict, exact **public AND private**
R455/R456 evidence-parity gate. A speedup threshold is **not** a test
success criterion; noisy values or regression are reported rather than
hidden. These synthetic microseconds/milliseconds do not establish
actual owner-inventory performance, real game FPS, network latency,
JVM startup, source parity or version compatibility.

Run without owner input:

    python -B tools/r468/benchmark_batched_thresholds.py --pairs 5 --iterations 8

## Verification, custody, and safety

15 new synthetic and fake-owner tests cover complete intersection,
duplicate opcode sites, mismatching targets, malformed/oversized input,
missing current JAR and CLI redaction, source mutation during a census
caught by final SHA, full public/private R459/R467/R468 parity,
all timing-mode evidence parity, no-opcode controls and budget refusals.
New Windows/Ubuntu × Python 3.11/3.13 CI also runs inherited R467-R442
regression suites and a separate inherited Recovery CI.

This is **static read-only diagnostic tooling**; it does not compile, run,
inject or optimize the actual SpawnPK client. The full original source
recovery, asset parity, runtime assembly, latency and historical R421
approval remain unverified. No production write-fence change, history
deletion, promotion, PR merge or release is authorized.
