# R134 — original-client dependency provenance before repairing the v309 source tree

The user’s primary objective is the **complete original client**, versioned and compiled from deobfuscated Java in `recovered-source/v309/src/` ([milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004)). A compilable decompiler-derived project is **not automatically faithful** to the original.

## Actual private pinned-input findings

A **read-only** comparison of the supplied client-only `SpawnPk-Decompiled-main (3)(2).zip` (SHA-256 `2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536`) and exact pinned original v309 client JAR (SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) found:

| Java source/import inventory | Count |
|---|---:|
| Candidate client Java files | **1,271** |
| Parsed explicit Java import declarations | **7,053** |
| Matching exact classfile path in original v309 | **956** |
| Present by candidate Java filename, original identity **unverified** | **3,042** |
| JDK/possibly external API namespaces, **not independently verified** | **2,980** |
| Possible original JVM nested class paths | **15** |
| Unresolved or static/wildcard import ownership | **60** |

The final 60 include **58 explicit imports without a matching exact original classfile or candidate Java file path**, and two static/wildcard imports not resolved by this path-only audit. Many of the 58 are Lombok annotation imports, which are a source-build dependency rather than necessarily original executable class dependencies. Also present are a JVM-management API, an unresolved obfuscated Apache Commons import, and **four Gson imports in a single candidate-only loot-history source class**.

**Important evidence distinction:** the candidate `rs/plugins/loottracker/LootHistoryStore.java` explicitly documents replacing the original client’s historical loot storage with new JSON persistence; it imports Gson classes that **do not exist inside the original v309 JAR**. That is evidence this workspace contains a later implementation/addition, not merely recovered original code. Do **not** call Gson a required dependency of original v309 merely because the current candidate source needs it, and do **not** erase the original loot-history storage merely to satisfy javac.

The current candidate also imports `org.apache.commons.a.d_`, whereas the exact original archive contains no `org/apache/commons/a/d_.class`. Its neighboring `org/apache/commons/a/F.class` **does exist**. This unresolved import may reflect incorrect decompiler renaming, not proof that original Java requires a missing third-party artifact. Independently verify the original owner/member and source callsite rather than synthesizing a stub.

## R134 intake tool

`private_v309_source_dependency_frontier_r134.py` consumes **exact SHA-pinned source and original JARs**, uses R126’s safe ZIP source extraction and R125’s original class inventory, and creates a SHA-pinned import-spelling preflight. It distinguishes original exact class path, candidate Java filename, possible nested class, JDK/other external API, and a missing *path-match*. Output is aggregate-only by default; explicit `--private-imports` writes path/name-level evidence into a **fresh private report**. Input client or Java code is never executed, and nothing is rewritten.

```text
python -m spk_recovery.private_v309_source_dependency_frontier_r134 \
  PRIVATE_CLIENT_SOURCE.zip PRIVATE_ORIGINAL_V309.jar \
  FRESH_PRIVATE_DEPENDENCY_FRONTIER.json \
  --source-sha256 EXACT_PRIVATE_SOURCE_ZIP_SHA256
```

**Limitations:** imports are a lexical-source preflight, *not* javac symbol resolution or bytecode attribution. Nested classes, static imports, on-demand imports, reflection, full dependencies, actual Java compiler errors and provenance are not certified. A class absent from the original client JAR may legitimately be supplied by an independently pinned external library, or may be genuinely newly written. Neither is accepted automatically. Hosted CI uses entirely synthetic ZIP and class identity fixtures.

## Actual compile frontier inherited from private research

The existing v309 candidate’s earlier, separate **provisional** source compilation reported 1,301 input Java sources and 118 javac errors before filtering; a provisional external classpath/filter yielded **seven remaining compiler diagnostics** (Gson plus an unresolved Commons type), and supplying separately sourced Gson reduced the error count further. However, that provisional binary dependency capsule is derived from **9,326 original non-`rs/` classfiles**, and prior research found one direct constant-pool link from the nominally external capsule back into `rs/`. Thus it does **not** yet satisfy a fully independent, certified, zero-project-binary-fallback original source-build gate.

The next work is to separate source-owned first-party types from independently authorized third-party libraries, remove or isolate nonoriginal additions from an original-v309-targeted compile profile, resolve incorrectly renamed source imports using original JVM evidence, and repair full source compilation with a clean, pinned classpath. Do **not** substitute the original `rs/` JAR as a compile dependency.

This workstream is client-only. No user account data, cache assets, raw decompiled source, original client JAR or nonoriginal server code is committed.
