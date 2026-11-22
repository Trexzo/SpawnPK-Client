# R460 — Reproducible performance comparison for nested R458 vs consolidated R459

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R459 draft PR #1256, verified 4/4 Windows/Ubuntu tests AND independent Recovery CI on `a6f383cb`.  
**State:** DRAFT / UNMERGED / NO CLIENT OR HISTORY MODIFICATION.

## What this actually benchmarks

R459 introduced a separate read-only coordinator that reuses immutable, exact-SHA admitted Java11 class bytes across R450–R458 analysis. In contrast, R458's legacy `inspect()` invokes R457→R447 nested audits, each repeatedly observing the full current source/class/dependency inventory and rereading classfiles. To avoid claiming improvement simply from code structure, R460 **measures the two real implementations** against **the exact same inputs**, checks shared results, and clearly separates performance metrics from correctness evidence.

`tools/r460/benchmark_consolidated_inspection.py` runs both R458 and R459 in paired comparisons, using an alternating **AB/BA** execution order and configurable 1–12 timed rounds per mode (3 by default), plus 0–3 untimed warmups (1 by default). It checks that exact original v309 inventory, isolated R421 class/source totals, `invokedynamic` instruction site count, and `CONSTANT_Dynamic` load count **agree** on each pair. If any shared evidence differs, the benchmark **refuses** to report a successful comparison.

The benchmarks collect three independent kinds of measurements:
- **Wall-clock latency:** `time.perf_counter_ns()` around each complete, separately SHA-guarded `inspect()`, summarized by median/min/max milliseconds. These runs do not include instrumentation overhead.
- **Bounded file I/O:** a separate instrumented run intercepts the already existing `scanner.read_bounded_regular` call using a temporary Python mock, then counts read calls and bytes returned by **category only**: rebuilt classes, Java source, preferred/alternate dependency JAR, original v309 JAR, and other. It restores the original reader on exit. This is an upper-level scanner I/O count, **not** physical disk bytes or cache misses; no file paths are printed.
- **Peak Python allocations:** another separate pass uses `tracemalloc` to measure Python-traced peak allocation, **not process working set/RSS**. It does not distort timing samples and is stopped on both successful and failed runs.

The benchmark performs its own additional complete `r446.observe()` before and after all comparisons plus a reread of the original exact SHA-pinned v309 JAR. Each legacy/consolidated `inspect()` already runs its own strict owner-custody SHA gates. The benchmark rejects mutations to any source, class, or dependency inventory and refuses changed or missing pinned original archives.

## Synthetic public CI versus owner measurements

Public CI uses the existing **invented two-class R421 owner-isolated TEMP fixture** with tiny fabricated original/dependency JARs and test-patched SHA constants. It exercises real R458 and R459 `inspect()` implementations. These tests are for **implementation and read-count correctness, not a realistic client-scale speedup claim**. Synthetic timing depends on GitHub runner load, small invented method bodies, OS cache and Python allocation behavior. A ratio below 1 is reported as-is; CI never asserts a fixed speedup. Tests check that R459 reads each synthetic rebuilt class three times in total (two full R446 SHA scans + one shared evidence read), whereas the deeply nested R458 reopens it more often. The output uses the explicit `data_origin=invented_public_fixture` label and `real_owner_performance_measured=false`.

Synthetic benchmark command:

```powershell
python -B tools\r460\benchmark_consolidated_inspection.py --synthetic --iterations 3 --warmups 1
```

The runner temporarily creates the fabricated fixture in OS TEMP, cleans it through unittest registered cleanup, prints only aggregate JSON, and never touches an installed client, real recovered source, settings, credentials, gameplay history or persistence journals.

Once the authorized owner's PC is accessible, the **explicit** real owner comparison can be run using an **already present, exact SHA-pinned v309 archive**, with no copying or GitHub upload:

```powershell
python -B tools\r460\benchmark_consolidated_inspection.py --owner-original-v309-jar '<owner-local exact original v309 client.jar>' --iterations 3 --warmups 1
```

This real mode reads only the exact R446 owner-isolated R421 source/class/dependency roots and the user-supplied pinned original JAR. It does not write results to disk, create manifests, import or compile a JAR, launch Java, or touch runtime settings. Because the nested R458 audit can be expensive on a large tree, maximum timed rounds and warmups are intentionally capped, and all read/output limits remain enforced. Real run must retain `real_runtime_latency_or_FPS_measured=false`: this is **offline audit throughput only**, not client gaming FPS, packet latency or JVM hot-path improvement.

## Safety, validity and limits

Default stdout contains only aggregate counts, no user-owned file paths, source/class names, hashes, method names, resource filenames, or byte payloads. No private reports are generated; the benchmark does not accept an output destination. It requires every examined report to continue denying historical full R421 approval, merge and release. The original v309 JAR SHA and 10,502/419 inventory are inherited from the existing owner paths; public synthetic tests only use patched invented equivalents.

**20 new synthetic tests** enforce count parity, improper release/historical flags denial, read-category aggregation, stable timer units, exact per-class read reduction, correctly separated timing and tracemalloc, privacy of stdout, CLI modes, tampering after admission, and benchmark input limits. CI runs Windows/Ubuntu × Python 3.11/3.13, plus all inherited R459–R445, R442 and R426 regressions. The workflow also prints one explicitly labeled invented-input benchmark JSON for visibility but does not persist owner paths or publish real data.

R460 does **not** yet prove any improvement on real R421 owner source, original v309/v312 JAR, gameplay FPS, network latency, JVM linking, asset packaging, compilation, runtime startup, UI, account login or automated task behavior. Owner desktop `DESKTOP-LTXXO4K` was offline (last seen 161 hours ago) during initial R460 inspection. The historical independently approved R421 full manifest is still missing: a fresh full SHA inventory is **not** a replacement. No R415/R417 persistence marker/write-fence alteration, game player-history read/write, client installation, PR merge or release is authorized.

**Keep R460 draft/unmerged until owner-side real inputs are independently measured and reviewed.**
