# R196 — actual R15 Java dependency frontier

The uploaded candidate's client Gradle build targets Java **11** (`options.release=11`), not Java 9. It declares `com.google.code.gson:gson:2.11.0`, Lombok compile-only plus annotation processing, and a vendored `client/libs/vendored-unidentified.jar`. The archive provided for this analysis contains no JAR entries. The past JDK-only diagnostics therefore do not constitute a legitimate full dependency-resolved build.

A read-only import inventory of all 1,274 R15 Java files identified the following unresolved *direct-import evidence*: `javax.inject` (73 affected files), `org.slf4j` (67), `com.google.inject` (38), `gnu.trove.f.b` (27), `com.google.a.b` (22), `javax.annotation` (21), `gnu.trove.i.a` (10), `org.yaml.snakeyaml` (6). These groups overlap. Obfuscated `com.google.a.*` imports require archive/class identity review; do **not** substitute Maven libraries by guessing. This is source-import analysis, not proof that each reported class is actually absent, nor a root-cause count.

New `tools/source_import_frontier_r196.py` performs this analysis on a supplied private ZIP and writes a private JSON report. Dedicated `tests/test_source_import_frontier_r196.py` and a cross-platform GitHub Actions workflow use synthetic Java only. No original private Java files or client binaries are published here.

Next acceptance gate: collect the exact approved third-party dependencies with verified artifact hashes, establish the real Gradle Java 11 compilation profile, then recompile the complete private candidate and distinguish remaining source faults. No original-client JAR fallback, invented placeholder class or unverified source parity.
