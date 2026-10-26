# Original SpawnPK v311 R121 — 85-class integrated private Java9 source build

**Evidence date:** 2026-10-24. Owner-original v311 client JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. All reconstructed owner Java sources, original/compiled game classes and private verification tooling stay off public GitHub.

## Verified integration, not new class discovery

R121 integrates **both previously privately accepted R120 scene-overlay registry JVM classes** with the R119 83-output source build in **one Java9 `javac --release 9` invocation**. Exactly **84 private Java9 source inputs** generate **85 selected original-named classfile outputs / 8,585 previously accepted original JVM instructions accounted for**. The compiler also emits temporary donor owners that are discarded; these are **not original source-recovered game classes**.

| Original JVM output | Contribution to integrated build | Original JVM instruction parity | Rebuilt class SHA256 |
| --- | --- | ---: | --- |
| `rs/runelite/b/a.class` | Two independent CopyOnWriteArrayList listener registries | **16/16** | `0a8b7fd7b139d099977f9b18d67fb9c6f2c1e1c8a551e7bdcf75917b7a4c709b` |
| `rs/runelite/b/a$a.class` | Nested functional scene callback interface | **0/0** (exact original declaration / method descriptors) | `2ace01bb6f5c33bf881c06f3b718e48f107b58ec3a5a0be4ff029ce3c99bd6ed` |
| 83 original-named R119 outputs | Previously accepted, unchanged | **8,569 retained** | **83/83 previous rebuilt SHA256 fingerprints identical** |
| **R121 one common build** | | **85 classfiles / 8,585 original instructions accounted for** | |

There are **ZERO new distinct class identities or newly counted instruction witnesses** in R121. The cumulative accepted original-v311 recovery ledger therefore remains **118/1,184 DISTINCT original JVM class identities / 10,054 exact matching JVM instructions across separately verified source-island builds**. R121's **85 / 8,585** measures the largest *single* output group, not a single 118-class source build.

### Compiler inputs and original identity

The integrated compiler stages the original R120 source `rs/runelite/b/a.java` with the 83 R119 Java input sources. R120's compiler-only nested interface name `Listener` and temporary `Object` callback parameter are restored to the original nested `a$a` identity and `rs/a/a` method parameter descriptor on **copied emitted classfile UTF8 constant-pool metadata only**. The executable `Code` and exception handler tables remain untouched. The missing `rs/a/a` original scene model is **not** compiled or faked.

Only the genuine original-v311-JAR `javax/inject/Singleton.class` annotation binary is additionally supplied to the previously authenticated real vendor-only GNU Trove, Google and LWJGL compiler archives. The Java compiler classpath contains **zero original `rs/` game binary classfiles** and no invented game implementation stubs. Previously reviewed reversible class/package collision aliases remain; the temporary original-UNRECOVERED `rs/k/e.class` renderer donor owner is discarded, **not** promoted as reconstructed original source.

### Clean private replay and refusal evidence

The owner-private `SpawnPK-v311-R121-85-Class-Private-Integrated-Sources.zip` was freshly extracted and independently verified against the exact pinned original JAR. Archive **SHA256 `664ddd352428388a7f78c2e6fd3779695d2c9a21ad60d9e8e60c7b08f67cd9fe`**, **257,707 bytes / 155 ZIP entries**. It contains private reconstructed source, manifests, verifier/probes and README, **no original game JAR, compiled original or reconstructed game/vendor class binaries, assets or credentials**; it is **not uploaded publicly**.

- SHA-pinned source/tool/JAR/class checks; exact **85/85** selected original-name output set; **83/83** previously rebuilt R119 fingerprints byte-for-byte unchanged and R120's two independently accepted rebuilt hashes unchanged.
- Original-vs-rebuilt `javap -p -s -c` declaration, offset, operand and ordered JVM instruction parity: registry **16/16**, nested interface **0/0** executable instructions with exact method metadata.
- Headless original-vs-rebuilt behavior observations: **R120 20/20**, **R114 20/20**, **R117 24/24**, **R116 17/17**. The R120 and R116 probes still use the owner-original JAR as a **trailing RUNTIME-ONLY** metadata fallback for the unrecovered scene model and outer renderer respectively; original game binaries are **never** on the compiler classpath. The R114/R117 probes do **not** require the original JAR at rebuilt runtime.
- **9/9 private deliberate-invalid checks correctly refused**, including a changed actual registry getter JVM algorithm after *both* candidate source and built-class SHA-256 fingerprints were repinned. The mutated 16-instruction sequence is still rejected by original instruction comparison. The privately replayed clean ZIP passed all nine.
- The earlier large historical behavior batteries were not rerun wholesale; certification of previous classes relies on unchanged compiled class hashes plus the bounded probes named above.

[Public synthetic-only Java9 integration test](../tests/test_v311_synthetic_registry_common_build.py) uses invented Java names and source unrelated to the original game. It checks retention of existing compiled fingerprints, integration of a nested functional interface, deterministic output, and real mutated JVM-code detection. Hosted CI is a separate public synthetic safety check and **does not validate private original binary parity**.

### Remaining blockers

- Original renderer `rs/k/e`: **17/36** accepted direct original project-type dependencies.
- Original scene model `rs/a/a`: **7/14** accepted direct original project-type dependencies.
- Both original parent implementations remain unrecovered. Seven provisional scene/tile candidates remain excluded. There is no whole-client source-build, full original classfile byte identity, GPU/native graphics, UI/gameplay or live integration acceptance.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. No manual gameplay test is needed for source-only R121.
