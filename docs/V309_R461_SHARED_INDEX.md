# R461 — ephemeral shared Java 11 constant-pool index

**Parent:** R460 draft PR #1261 at 27a4e79.  
**Status:** DRAFT / UNMERGED / SOURCE-FREE SYNTHETIC VERIFICATION.

## Findings

R460 showed that R459 removes recursive full-file scanning, but every
SHA-admitted classfile is still tokenized three separate times by
R453.parse_class, R458.scan_class and R450.classfile_evidence.
The repeated constant-pool decoding is a possible remaining CPU hotspot.

R461 introduces a pure in-memory Java11 constant-pool decoder in
tools/r461/shared_constant_pool.py. It creates an immutable dataclass containing
the exact existing bytes object, CP tag/entry tuples and the offset immediately
following the constant pool. The optional shared_pool parameter in R450, R453
and R458 replaces **only** their redundant CP tokenization loop and preserves
all their independent name, descriptor, member, handle, BootstrapMethods,
Code, Signature, opcode and CP reference checks. The unmodified public
functions still decode independently when shared_pool is omitted.

The index is admitted only for the identical immutable bytes object by identity
(not merely a matching path or hash); it is never cached globally or persisted.
The existing R459 coordinator gets an optional shared_pool_factory, omitted by
default; only R461 invokes it. There is one index per class evidence pass,
three total bounded class reads per class remain in place (two full inventory
SHA scans plus one evidence read), and original-JAR and dependency checks are
unchanged.

## Validation and controls

- Pure parser parity is checked against independent R450/R453/R458 on
  fabricated Java11 invokedynamic, ConstantDynamic and unused CP samples.
- Malformed/incompatible dynamic callsites are still rejected using the
  **same parser-specific error** as the original independent path.
- Wrong bytes identity, malformed CP tag, truncated CP, non-Java11 class,
  mutable input, CP-count errors and attempted mutation of the frozen index
  are rejected.
- Full invented owner-tree R459 and R461 aggregate reports **and private
  candidate worklists** must compare exactly; no class paths or source bytes
  appear in published results.
- Counterbalanced pairs compare the default R459 independent path with the
  opt-in R461 shared-index path on identical complete SHA-observed inputs;
  original pinned JAR is checked again after each pair. Exact read count
  parity must hold. Measured wall/CPU/peak allocation numbers include
  instrumentation overhead; no minimum speedup is asserted.
- No source or JAR bytes, source/class names, per-file SHA maps, historical
  evidence, player history or deletion journals are emitted or persisted.
  No gameplay execution, compilation, release, merge, deployment or historical
  R421 custody approval.

This is a **tokenization reuse** optimization, not a single complete JVM
classfile parser or proof of source parity. Remaining parser-specific
semantic checks are intentionally separate to keep independent evidence.

## Authorized owner-only usage

From the repository root on the owner's local computer containing the exact
pinned original v309 JAR and existing isolated R421 TEMP trees:

    python -B tools/r461/benchmark_shared_index.py --original-v309-jar "<owner-local exact v309 client.jar>" --pairs 2

This command is read-only, generates aggregate JSON on stdout, creates no
private report file and never starts the game. The optional resource companion
is excluded so the comparison uses matched inputs.

**Do not extrapolate synthetic speedup numbers to real SpawnPK client
performance.** The owner desktop, real class/JAR completeness, asset packaging,
v312 runtime acceptance and actual gameplay remain unverified. No changes to
R415/R417 persistence write fences or deletion-intent evidence are authorized.
