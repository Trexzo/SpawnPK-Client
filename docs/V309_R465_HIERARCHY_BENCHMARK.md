# R465 — overlap-heavy synthetic class-hierarchy benchmark

Parent: R464 draft PR #1265, SHA 092904bb0651dbc1afb55a800933c2d96d8376f6.
Status: DRAFT / UNMERGED / FABRICATED INPUTS ONLY.

## Reason

R464 eliminates duplicate ancestry and member-resolution calculation *when*
R455 dependency-member analysis and R456 opcode-site analysis investigate
the same member owners/references on the same combined class graph.

The previous R464 fake-owner microbenchmark has **zero cache hits and zero
ancestry/resolution calls**. Its wall-time ratios therefore cannot measure
R464's intended benefit. We must not claim those tiny synthetic timings
prove any game or owner-host improvement.

R465 creates a deterministic, controllable, entirely IN-MEMORY benchmark
with synthetic R453 ClassMembers data. It does not parse or download any
SpawnPK original, reconstructed Java source, JAR, asset, or persistence record.

## Workload design

Default benchmark cases:

| Synthetic owners | Signatures per owner | R455/R456 overlap |
| ---: | ---: | --- |
| 24 | 8 | Yes |
| 96 | 8 | Yes |
| 192 | 8 | Yes |
| 96 | 8 | No (negative control) |

Each owner has a separate synthetic rebuilt caller and a selected dependency
owner that extends one of four intermediate classes, which inherit from a
shared root. The root declares public, private and static members; the member
references target owners that have inherited or noninheritable signatures.
R455 analyzes all incoming constant-pool member references; R456 analyzes
actual modeled invoke sites when overlap is enabled. The negative control
contains no R456 opcode sites, so a cache can have **zero reuse** despite the
same R455 reference workload.

Sizes are bounded to at most 256 owners and 16 signatures per owner; results
never include individual class/member names, descriptors, paths, hashes or
private evidence.

## Correctness and performance

- Run R455 + R456 legacy path on generated immutable records.
- Run R455 + R456 with the R464 scan-local graph cache on the **same inputs**.
- Compare the entire pair of return values, including both private synthetic
  candidate worklists, not only selected summary counts.
- Independently count R454.ancestry and R454.lookup calls outside timing:
  with overlap, expected calls are owners * 2 and owners * signatures * 2
  without caching vs owners and owners * signatures with caching.
- Verify no-overlap control preserves call counts and produces **zero cache
  hits**, rather than inferring that caching always helps.
- Run at least two counterbalanced timed pairs per case, median wall and CPU
  times plus Python-tracked peak allocation. Timings include tracemalloc and
  are subject to hosted CI noise. No speedup threshold is asserted.
- Public cross-platform CI (Windows/Ubuntu × Python 3.11/3.13) also runs the
  existing R464–R442 inherited SHA, parser parity and custody denial tests.

**Scope limitation:** R465 is an IN-MEMORY microbenchmark of R455/R456
analyzers. It does not perform R446 full SHA scans, ZIP/archive reads, owner
inventory collection, actual class decoding, or game compilation/runtime.
Those gates are still exercised by inherited R464 and R459 tests and must
not be bypassed in any owner-private workflow.

## Run locally

    python -B tools/r465/benchmark_hierarchy_overlap.py --pairs 2

Optional bounded focused workload:

    python -B tools/r465/benchmark_hierarchy_overlap.py --pairs 2 --sizes 24 96 192

The optional sizes mode only tests overlap cases; default also tests the
no-overlap negative control. Script prints aggregate JSON to stdout and
creates no files; it never opens game binaries, player records, owner history
or live client paths.

Do not extrapolate the in-memory synthetic ratios to actual client latency,
full-owner audit throughput or "100% source coverage". Runtime compilation,
packaging, actual private source/class parity, version compatibility and
independent historical R421 custody approval remain unverified. No merge,
release, promotion, game launch, or persistence write-fence changes authorized.
