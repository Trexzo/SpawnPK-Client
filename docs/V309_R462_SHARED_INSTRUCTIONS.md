# R462 — one class-local decoded JVM instruction stream for static recovery

Repository: Trexzo/SpawnPK-Client
Parent: R461 draft PR #1262 (a3750e8)
Status: DRAFT / UNMERGED / SOURCE-FREE SYNTHETIC VERIFICATION

## Hot path

R461 eliminates three separate constant-pool tokenization loops, but
R458.scan_class, R456.decoded_sites, R451.trace_method,
R452.analyze_method and R450.classfile_evidence each separately call
R450.instructions on the SAME JVM method Code body.

R462 adds an ephemeral per-class instruction index keyed by exact immutable
method Code byte contents. Each *distinct* Code stream uses R450's existing
bounded, strict instruction decoder once; subsequent analyzers share its
frozen opcode/PC/operand tuple.

- R458 validates invokedynamic and CONSTANT_Dynamic operands independently.
- R456 validates typed field/method opcode refs independently.
- R451 and R452 still perform their separate strict stack/control-flow
  resource-tracing analyses.
- R450 independently validates Code/Signature metadata and proximity.
- Legacy R450/R451/R452/R456/R458 default calls decode independently.
- R459's shared_instruction_factory is optional and does not change
  the default SHA-verified audit path.
- R462 opts into both R461 shared constant-pool tokenization and the new
  shared instruction decoder. One cache per compiled class; none persists.

A cache entry is keyed by method Code byte value, not label, class name or
path; only *exactly identical* code bytes share instruction boundaries.
Decoder errors are never cached. Malformed/truncated/reserved opcode
streams still fail with the original decoder refusals. Total distinct code
bytes, instructions, and number of distinct bodies per class are bounded.
All cached data remains memory-local within the one class parse.

## Verification

- Exact independent output parity includes both public aggregate results
  and private name-only reconstruction candidate details on fabricated
  owner trees. Existing R459 cross-decoder dynamic and member counts remain
  enforced.
- Targeted pure bytecode checks include standard opcodes, wide,
  tableswitch, lookupswitch, misaligned/truncated and reserved instructions.
- Synthetic Java11 invokedynamic and ConstantDynamic classification agrees
  with the original R458 results.
- Only one canonical decoder call per unique Code bytes, reused across
  R450, R451, R452, R456 and R458. Cache hit/miss totals are aggregated
  but never include method paths, instruction operands or raw Code bytes.
- Counterbalanced pairs compare R461 (independent Code decoders) versus
  R462 (shared decoder) on identical SHA-observed input trees, with
  additional full before/after R446 scans and pinned-original re-read.
  No bounded-reader class read count changes.
- Cross-platform synthetic CI runs Windows and Ubuntu with Python
  3.11 and 3.13 plus inherited R461/R460/R459/R458/R456/R452/R451/R450,
  R442 correctness tests.

No arbitrary source may be used as a historical R421 approved manifest.
No user histories, deletion journals, client startup, source compilation,
production write-fence changes, asset packaging, runtime replacement,
release or merge is authorized.

## Read-only owner test (when inputs are available)

    python -B tools/r462/benchmark_instruction_index.py --original-v309-jar "<pinned owner-local v309 client.jar>" --pairs 2

The benchmark emits aggregate JSON on stdout only and does not produce or
install a client or export private bytecode. Timings are instrumented with
tracemalloc and bounded-read counters, so do not treat synthetic CI results
as owner-PC performance. Actual client completeness, v312 compatibility,
FPS/gameplay latency and resource packaging remain unverified.
