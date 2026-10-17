# R199 — replay entire R15 candidate with explicit Java 11 target

This is an actual local complete-source compiler replay, not an import-only estimate. Extracted all **1,274 Java files** from the private R15 ZIP and ran the full JDK 21 `javac --release 11 -proc:none -g:none -encoding UTF-8 -Xmaxerrs 3000` profile without any original client classpath or external JARs.

**Result:** 2,002 javac errors (R15 had previously reported 2,002 with the less accurate unpinned JDK release profile). The corrected release level therefore does **not** change the raw error count in this dependency-free comparison.

Actual compiler diagnostic groups:

| Category | Count |
|---|---:|
| Cannot find symbol | 1,420 |
| Missing package | 563 |
| Invalid override | 12 |
| Module not functional interface | 3 |
| Interface expected | 2 |
| Incompatible look-and-feel | 1 |
| List vs Collection type | 1 |
| **Total** | **2,002** |

High-frequency missing packages: `org.slf4j` (136), `javax.inject` (95), `com.google.inject` (59), `gnu.trove.f.b` (30), `com.google.a.b` (26), `javax.annotation` (23). Not all of these can safely be resolved from names alone: relocated and obfuscated owners need exact artifact verification.

Highest diagnostic concentrations by Java source: `GpuRenderer.java` (217), `OpenCLManager.java` (136), `ObsidianSkin.java` (126), `RuneLiteSkin.java` (123), `PluginManager.java` (47), `EventBus.java` (37). The top four together produce **602 errors**, largely representing unresolved graphics and skinning library dependencies; 602 errors do not mean 602 independently broken Java methods.

Added `tools/javac_frontier_r199.py` and synthetic tests/CI to parse real `javac` stderr, report missing-package and per-source error pressure, and keep profiles comparable. Private full report: `SpawnPK_R199_JAVA11_DIAGNOSTIC_FRONTIER_PRIVATE.json` delivered in chat.

This is a third-party decompiled client candidate. No exact original v309 method equivalence is established and no complete client build is claimed. There is still no verified vendored JAR or full approved dependency classpath. Do not infer compiler root causes from raw diagnostic counts.
