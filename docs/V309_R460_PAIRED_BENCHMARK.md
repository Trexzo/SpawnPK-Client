# R460 — paired static-audit benchmark and hot-path attribution

Repository: Trexzo/SpawnPK-Client
Parent: R459 PR #1256 (a6f383cb)
Status: DRAFT / UNMERGED / OWNER-PRIVATE INPUTS UNAVAILABLE IN PUBLIC CI

## Question

R459 removed nested audit recursion but retained two complete R446 source/class/dependency observations, one class evidence read, a second pinned-original read, and several independent in-memory parsers. Does it actually reduce read volume and wall time against R458 on the same stable inputs, and where does the remaining time go?

R460 adds an alternative read-only profiling utility. It does not change the R458 or R459 analyzers or authorization requirements.

## What is measured

- Paired R458.inspect (legacy nested R447–R458 chain) and R459.inspect (consolidated class-evidence path) on the same inputs.
- perf_counter_ns wall time, process_time_ns process CPU time and tracemalloc peak Python-traced allocation.
- Calls and returned bytes through scanner.read_bounded_regular, grouped only as Java source, compiled class, JAR or other (never by private path).
- Inclusive stage timings and call totals for complete R446 inventory, original/dependency ZIP central-directory inspection, R453 member CP, R458 bootstrap/dynamic, R450 Code+Signature/resource, R455 dependency selection and R453–R458 aggregates. Stage times overlap and must not be summed into exclusive CPU percentages.
- Check shared result parity (original class/resource counts, rebuilt source and class counts, dynamic callsites, constant-dynamic loads, bootstrap handle-argument sites); refuse a discrepancy.
- Perform full R446 source/class/dependency SHA inventories before and after each pair, separate from measured invocations; verify pinned original JAR again. This is extra work, intentionally outside the timed regions, and is not a substitute for either analyzer's internal integrity scans.
- Alternate comparison order across successive pairs (R458→R459, R459→R458, etc.) and report medians rather than selecting one fastest run. Default 2 pairs, maximum 4.
- Assert exactly 3 total compiled-class bounded reads per class for the consolidated path (initial inventory, evidence pass, final inventory).

The read counters instrument the common bounded file reader. They do not claim to count every OS-level file read, directory listing, ZIP memory operation or Python allocation. Profiling and tracing have overhead, so wall/CPU numbers are not uninstrumented production timings.

## Owner-only invocation (once original inputs are available)

Run from the repo root, from a clean branch checkout, on the owner's authorized local PC. No Java/game process is started:

    python -B tools/r460/benchmark_inspection.py --original-v309-jar "<exact owner-local pinned v309 client.jar>" --pairs 2

Default JSON goes only to standard output, with aggregate timings/counts.
No class names, source bytes, original client bytes, full SHA maps, private directory names, player history or journal content are serialized. The optional resource companion is deliberately excluded from this benchmark so both audit paths exercise the same no-companion mode.

Real owner results must be labeled measured owner-private workload, with platform, Python version, cold/warm filesystem context and repeat count recorded separately by the owner. Do not treat CI fixture results as real v309 workload performance.

## Expected interpretation and next optimization leads

1. File-read pressure: legacy R458 should reread class files more often due to nested inspections. R459 deliberately still hashes each class twice and reads it once for evidence. Any future attempt to eliminate those required reads must provide an independently validated replacement for the original TOCTOU safeguards; R460 makes no such change.
2. Remaining parsing overhead: R459 still independently runs R453 parse_class, R458 scan_class, and R450 classfile_evidence over each immutable byte string. These may share a future validated bytecode/constant-pool index, but cross-parser disagreement detection should be retained as an independent oracle before any parser is removed.
3. Control-flow workload: R452 bounded CFG/resource interpretation is part of R450 Code observers. Compare its state and method counts with the code_signature_resource_parse stage before allocating optimization effort.
4. Archive/dependency workload: zip_directory_admission, dependency_selection and repeated bounded JAR reads can matter on larger real snapshots. Avoid skipping pinned SHA verification merely for performance.

The public R460 test constructs invented Java11 classes, sources and ZIPs using inherited R458/R459 fixtures. It checks read reduction, shared semantic parity, mutation refusal, no private output and redacted CLI errors. Synthetic timing may be reported in CI as synthetic only, never generalized to the unavailable owner desktop.

## Non-goals and unchanged blocks

No compile or asset packaging, no JNI/JVM loading, no client replacement, no v312 runtime compatibility claim, no historical R421 custody approval, no player history or deletion journal access, and no R415/R417 write-fence override. PR remains unmerged and no release is authorized.
