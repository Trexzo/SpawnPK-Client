# R137 — reproducible private v309 Java compiler frontier, without `rs/` binary fallbacks

The final goal is still the **entire versioned, independently compilable deobfuscated original SpawnPK client source tree** in `recovered-source/v309/src/` ([milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004)). A decompiled workspace with substituted features or an original-client-derived binary classpath is not an accepted equivalent of the original source.

## Why a separate diagnostic is necessary

R135 merged the first original-bytecode-guarded, private Java AST source edit. R136 [#1023](https://github.com/Trexzo/SpawnPK-Client/pull/1023) identifies original client code hidden in nominally external `com/`, `org/`, `gnu/` and `tools/` classfile namespaces. An independent local preflight of original v309 SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` counted **10,502** classfiles (1,159 `rs/`, 9,343 non-`rs/`), including **eight** directly referring to `rs/`, and **zero** extra transitive dependents. This left 9,335 *provisionally* untainted binary dependencies, but **did not independently prove them to be third-party code**.

To establish a reproducible compiler-error baseline before source repairs, a private, manually replayed exploratory javac run staged 1,271 source files from ZIP SHA256 `2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536`, built a temporary **unverified diagnostic-only** classpath JAR containing the 9,335 non-`rs/` and non-tainted original classfiles, and ran `javac --release 11 -proc:none -implicit:none -encoding UTF-8 -Xmaxerrs 3000`. It **FAILED with 614 observed compiler errors**: 511 unresolved symbols, 58 missing-package errors and 45 other compiler errors. No original `rs/` classfile was included in the explicit classpath. The candidate Java source was unmodified in that experiment, so it is **not** a measurement of R135's private alias patch. The diagnostic capsule was not published.

**Critically:** zero direct/transitive `rs/` links is not a full independent third-party provenance audit. This provisional compile is **NOT** Source Milestone acceptance, does **not** prove absence of first-party binary fallbacks, and does **not** establish an executable rebuilt client.

## Automated private compiler gate

R137 turns the provisional compile procedure into a single SHA-pinned, controlled diagnostic command. It:

1. Checks both original Jar and private decompiled-source ZIP hashes.
2. Uses R126's safe client Java ZIP intake and R136's JVM constant-pool + descriptor graph to exclude all original `rs/` classes and every identified direct/transitive game-linked non-`rs/` class.
3. Builds a **temporary, deterministic, private diagnostic-only** non-`rs/` classpath JAR (never published), with no `rs/` class members.
4. Stages all candidate Java sources in a temporary private directory, sets an explicit **empty sourcepath**, isolates the classpath to this temporary diagnostic capsule, disables annotation processors and implicit source compilation, clears environment classpath/JAVA_OPTIONS and compiles with Java 11 release rules. Never launches the original JAR or application code.
5. Returns only SHA pins, source/class counts, diagnostic category counts, whether javac failed, and deterministic hashes of the private stderr and capsule. **All source paths, symbol names, classfile bytes, stderr diagnostics and generated classfiles are destroyed with the temporary directory.**
6. Unconditionally reports `complete_original_client_source_build_accepted=false`, `non_rs_original_binary_capsule_certified_third_party=false` and `original_project_binary_fallback_fully_ruled_out=false`, even when a synthetic test compiles successfully.

Private invocation:

```text
python -m spk_recovery.private_v309_compiler_frontier_r137 \
  PRIVATE_DECOMPILED_SOURCE.zip PRIVATE_ORIGINAL_V309.jar \
  FRESH_PRIVATE_JAVAC_REPORT.json \
  --source-sha256 EXACT_PRIVATE_SOURCE_ZIP_SHA256
```

The original Jar's default SHA pin is exact v309. The report stays private, though its aggregate counts may be shared with the GitHub milestone. No original binary or decompiled source is uploaded to CI.

## Focused tests and next repair gate

CI builds an independent **synthetic original** with `rs.Game`, a clean external `ext.Clean`, a directly game-linked `ext.Bridge` and a transitively game-linked `ext.Indirect`. The test stages candidate Java that can compile only with the clean external class, and a negative candidate that tries to compile against excluded `ext.Bridge`. It rejects wrong original and source SHA pins, proves the diagnostic classpath is deterministic and the report never claims whole-source acceptance.

After real R137 CLI replay, prioritize *actual* unresolved source type identities and source-owned dependencies, quarantine proven post-original additions without deleting original functionality, and supply **independently verified/licensed** dependency source or binaries. A true clean-build gate must compile the entire reviewed original-derived source set with **zero original project binary fallback**, then verify mapped class/field/method parity, source bundle completeness and isolated runtime semantics.

This is strictly **client-only**. No independently written server/gameplay emulator code is involved.
