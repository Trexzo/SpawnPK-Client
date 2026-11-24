# R464 — share selected class-hierarchy evidence between R455 and R456

**Parent:** R463 PR #1264, exact approved-for-research commit f1ccfda0.
**Status:** DRAFT / UNMERGED / SYNTHETIC CI ONLY.

## Confirmed static audit hot path

After R459 loads the SHA-checked rebuilt classes and R455's selected preferred
dependency classes, R455.analyze walks ancestry and resolves inherited member
signature candidates for references in the reconstructed classes. R456.analyze
then walks the same combined class graph and frequently resolves the same
method/field signatures to compare bytecode opcodes with declaration flags.
Both invoke R454's bounded pure ancestry/lookup functions on equivalent
input records, but keep independent per-stage local caches.

R464 introduces tools/r464/shared_hierarchy.py with a **strict, bounded,
scan-local** graph index. The combined map is made from the exact immutable
R453 ClassMembers records already admitted by the audit. Both R455 and R456
admit the map independently with identical key sets AND exact record-object
identities before reuse. Only immutable R454 Ancestry and Resolution values are
cached. A missing/replaced record, wrong owner/ancestry pair, exhausted owner
or reference budgets causes fail-closed rejection.

The rebuilt-only R454.analyze remains a wholly separate, independent check:
its graph does not contain the selected dependency records and could legitimately
produce DIFFERENT results. No sharing with R454 or speculative JVM loader,
inherited visibility, linkability or runtime dispatch is authorized.

## Verification and metrics

Synthetic tests include a fabricated Caller->B->A inheritance relationship.
The same inherited foo()V signature appears in R455 dependency analysis and
in an R456 invokevirtual site. Both stages return identical public/private
results with the legacy path, while the shared graph performs **one ancestry
and one member-resolution calculation instead of two** on that case.

The full fabricated owner-tree audit must return exactly the same entire
public summary and private candidate worklist through R463 and R464. Paired
counterbalanced R463/R464 measurements retain the original pinned v309,
full before/after R446 source/class/dependency SHA inventories, nofollow
file readers, code/constant-pool cross-validator parity, and the identical
bounded classfile read count (3 reads per compiled class, total).

New graph input mutation, wrong identity, owner-chain mismatch, cache-budget,
unexpected private export and missing-original fail-closed tests accompany
inherited R463-R442 suites on Windows/Ubuntu × Python 3.11/3.13.

Owner-only read-only command:

    python -B tools/r464/benchmark_hierarchy.py --original-v309-jar "<pinned owner-local v309 client.jar>" --pairs 2

Outputs aggregate-only metrics on stdout, never class names, paths, private
hashes, raw source/JAR/class files, history, or deletion journal content.
Instrumentation overhead and tiny synthetic test sizes prevent extrapolation
to full private-owner performance. **A real-client speedup is unverified.**

The historical R421 custody manifest, complete class/source/asset parity,
JVM compilation/load/runtime and v312 compatibility remain unverified. No
production writes, R415/R417 fence changes, client launch, promotion,
deployment, merge or release are authorized.
