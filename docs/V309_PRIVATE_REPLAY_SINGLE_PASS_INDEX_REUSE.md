# v309 exact-private single-pass index reuse (research only)

## Problem addressed

Merged #883 offers a single local CLI for all five exact-client research lanes. The original implementation still did redundant work internally:

- #883 built each full v308/v309 class index for unique-literal and method-shape research.
- #883 ran the CP pairwise comparison (#878).
- The nested rival-owner lane (#879) independently rebuilt **both entire indexes** and reran the CP pairwise comparison, despite using the same exact SHA-pinned JARs.

This needlessly repeated class parsing across **10,472 v308 and 10,502 v309 classes**, duplicated potentially large in-memory index objects, and made the phrase "single index pass" inaccurate.

## New execution path

The standalone whole-archive rival scanner remains independent and unchanged when invoked normally.

The one-shot replay passes into that existing scanner the two class indexes that it has already constructed from the exact SHA-pinned originals, plus the content-addressed CP pair report it has just generated. The rival scan then performs only its required **candidate Code profiling and mutual whole-archive veto analysis**—not a second full class index pass and not a second pairwise CP-method run.

Reused objects are not an alternative authority: the scanner independently checks exact old/new original JAR SHA-256, lineage build fingerprints, unchanged 143/26 frontier, canonical class-lineage validation, global-field report integrity, all parent-report identity/acceptance counters, **full-body CP pair report digest**, exact source report chain, zero class parse errors, and complete old/new class counts. Missing, partial or mismatched caches fail closed instead of triggering a silent fallback. The cached class index's complete entry-name set is checked against the original JAR's central-directory manifest, including missing, extra and duplicate entry vetoes; this does not decompress the original class entries again. Original-JAR SHA-256 still supplies the byte-content authority.

## Regression evidence

- A synthetic original-JAR-backed test executes the same rival research logic through **standalone** and **cached** input paths, requiring byte-for-byte identical aggregate report data and deterministic report ID.
- The one-shot orchestrator test asserts that the exact same old index object, new index object, and original CP pair report object are forwarded.
- Negative tests cover a single missing index, a tampered CP report whose ID is stale, re-signed wrong client build data, incomplete cached indexes, changed original private JAR hash, and no-clobber/zero-acceptance behavior.

The exact-private full replay on the user's machine is still an independently required verification step. Hosted CI uses synthetic data, never the proprietary JARs. No private source, original JAR, class index, Code, member descriptor, CP value, or literal is uploaded to GitHub.

The public v309 recovery frontier is still ACCEPTED_INCOMPLETE with **143 unresolved field relationships**, including 26 descriptor-identity blockers. The refactor **cannot accept** a class or field mapping, and does not modify the Source M1 compiler recovery frontier.
