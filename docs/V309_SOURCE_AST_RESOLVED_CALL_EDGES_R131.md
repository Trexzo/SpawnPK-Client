# R131 — independently symbol-resolved source-Java call edges

The user goal is still a complete, standalone **client-only** `recovered-source/v309/src/` tree ([issue #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004)). The merged R127/R128 source/JVM comparison tools generated 501 structural *review candidates*; [R129 #1013](https://github.com/Trexzo/SpawnPK-Client/pull/1013) classifies matching graph relationships only after independently derived source and original JVM edge inventories. [R130 #1015](https://github.com/Trexzo/SpawnPK-Client/pull/1015) is the **original-JVM edge extractor**.

R131 adds the **source-Java half**, via `JavacTask.parse()` and `analyze()`, `Trees.getElement()`, and `Elements.getBinaryName()`. Its AST visitor examines explicit `MethodInvocationTree` and `NewClassTree` calls. It extracts the declaration-owner `rs/` binary class names from compiler-resolved symbols, never from ambiguous textual patterns or guessed imported types. Calls from nested/local classes are deliberately withheld to avoid wrong outer class ownership. Method references are recorded only as an excluded-count because they compile via `invokedynamic`; R130 likewise withholds invokedynamic owner attribution.

The source ZIP is exact-SHA-pinned and subject to the earlier R126 unsafe-archive, UTF-8, duplicate-entry, size and Windows casefold path gates. R131 writes Java to a private temporary directory but does **not** compile/generate Java game classes, execute game code, or run the original JAR. The trusted helper alone is compiled into an isolated helper directory. Javac source resolution uses a separately created **empty classpath and sourcepath**, `--release 11 -proc:none -implicit:none`; the compiler must resolve every candidate Java symbol against only supplied sources and permitted JDK classes.

**Fail-closed:** any missing dependency, duplicate/ambiguous type, unresolved method/constructor or Java source error rejects the entire result. A partial call graph must **never** be interpreted as a complete source-side verification. A successful synthetic source scan does not establish that all 1,271 private v309 candidate files can pass symbol resolution yet—R124 found unresolved Gson/Lombok/symbol and class/package compilation blockers, so a private full-source R131 replay may legitimately fail until those are repaired.

JVM invoke constant-pool owners and javac Elements declaration owners also can differ for inherited or erased calls. Matching R130/R131 edges therefore remains heuristic corroboration and cannot substitute for method opcode, descriptor, bootstrap and dispatch parity. No `CLIENT_CLASS` or `CLIENT_METHOD` identity is auto-accepted; no deobfuscated source files are rewritten.

## Private CLI

```text
python -m spk_recovery.private_source_ast_call_edges_r131 \
  PRIVATE_DECOMPILED_SOURCE.zip FRESH_PRIVATE_SOURCE_EDGES.json \
  --source-sha256 EXACT_SOURCE_ZIP_SHA256
```

Default private report is aggregate-only, SHA-pinned and has an edge-manifest digest. Explicit `--private-edges` adds `private_source_call_edges` to the **local private JSON** for R129's `source_call_edges` envelope field, never for a GitHub commit.

Synthetic CI compiles only the trusted AST helper and symbol-analyzes a three-file Java test fixture with direct static, virtual, constructor and interface invocations plus a method reference. Missing dependencies, duplicate declarations, malformed symbols and incorrect source hash must fail completely. The original v309 executable and private decompiled Java do not enter hosted CI.

## Next

Once all 1,271 source files can be symbol-resolved with explicitly pinned legal dependencies and no original `rs/` class fallback, combine independently sourced R131 `source_call_edges` and R130 `private_original_call_edges` into R129's private envelope. Review the resulting candidate contradictions, **then** seek method/callsite-level parity and stable semantic names before source-aware rewrites and full zero-fallback javac acceptance. No server-side reconstruction.
