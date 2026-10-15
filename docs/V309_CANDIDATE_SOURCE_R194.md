# R194 — larger Java source repair batch (private R14)

This batch changes **real Java method bodies** in the uploaded third-party source candidate, not just error-reporting infrastructure. It removes remaining Lombok `@SneakyThrows` annotations from **33 methods across 16 Java files**, replacing them with explicit catch/rethrow implementations that preserve the thrown `Throwable` object and original method declarations. This is NOT a claim of exact original Java source or JVM bytecode parity.

## Modified class clusters

- Network: `rs/network/Class258.java` — 5 methods.
- Secure/process: `rs/secure/Class305.java` — 4 methods.
- Plugin loading: `rs/plugins/PluginManager.java` — 4 methods.
- OSRS dependency scan: `rs/cache/osrs/util/OsrsMapDependencyScanner.java` — 4 methods.
- Cache I/O: `rs/cache/osrs/util/Class49.java` — 3 methods.
- Loadout serialization: `rs/gui/loadouts/io/LoadoutSerializer.java` — 2 methods.
- OS/network helper: `rs/pkg48/Class307.java` — 2 methods.
- One method each: `SkyboxDefinition`, `ShaderProgram`, `ConfigInvocationHandler`, `ClientUI`, `RuneliteColorPicker`, `AssetUpdater`, `TradingPostSearchPanel`, `NotificationManager`, `Class288`.

## Whole-tree compile (same exact diagnostic profile)

Complete uploaded third-party source set: **1,274 Java files**, JDK 21.0.12.1, `javac -proc:none -g:none -encoding UTF-8 -Xmaxerrs 3000`, no dependency JARs or original client binary.

| Candidate | Java files | Compiler errors | Warnings |
|---|---:|---:|---:|
| Original uploaded | 1,274 | 2,391 | 9 |
| R13 | 1,274 | 2,065 | 9 |
| R14 | 1,274 | **2,017** | **9** |

**48 fewer raw compiler errors than R13**, 374 fewer than the uploaded baseline. Diagnostic comparison identified no newly appearing `(source file, error category)` pairs in R14. Remaining compiler errors still prevent a whole-client build; no proof of bytecode parity or runtime equivalence is asserted from this compilation.

## Private output and reproducibility

Complete source archive: `SpawnPK_v309_FULL_SOURCE_R14_PRIVATE.zip`. It contains all 1,274 source candidates; `PRIVATE_MANIFEST.json` records per-file SHA-256 and 16 file-specific before/after witnesses, and `javac.stderr` retains the full private compiler diagnostic output. SHA-256 archive: `a654cdab358e2ab5866a796d5dff2ce21fcdf45f171358c34651a286c99700bf`.

GitHub provides a *generic* SHA-pinned opt-in rewrite producer at `tools/private_sneakythrows_rewrite_r194.py`; this producer does not contain original-derived game code or publish a source tree. It uses its own internal helper naming; do **not** assume its bytes produce the identical R14 private ZIP without re-running and verifying the candidate compilation. Synthetic Java9 tests test unchanged exception instance and method behavior.

**Hard acceptance boundary:** this is a third-party decompiled Java candidate, NOT the exact original v309 JAR or separately recovered private 1,279-source snapshot. Do not publish reconstructed Java without permission, or claim full original-client recovery or source-only compilation acceptance. Exact original class/method parity and verified dependency closure remain outstanding.
