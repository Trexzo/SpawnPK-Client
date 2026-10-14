# R131 — source-side method/constructor edge extraction from attributed Java symbols

The original client is **the only** target of this pipeline, tracked under [source milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). R130 provides the original-JVM invoke edge half; R131 supplies a genuinely independent decompiled-Java **source-side** edge inventory. Both are inputs to the tentative R129 callgraph classifier. Neither alone makes recovered class identities authoritative.

## Why symbol attribution instead of filename matching

The actual decompiled v309 workspace has 1,271 Java files, 1,321 named AST types, and only 28 named type spellings matching original `rs/` classfiles. Extracting source edges by searching for lexical patterns like `Class123.foo(` would create fake edges when variables or static imports shadow class names.

The R131 helper compiles **only its own trusted scanner**. It stages source from an exact-SHA-pinned ZIP, then uses `JavacTask.parse()` and `JavacTask.analyze()` with Java11 language rules, disabled annotation processing (`-proc:none`), no generated source compilation (`-implicit:none`), and an **explicitly empty external classpath/sourcepath**. It never invokes `task.generate()`, launches the decompiled client, or uses original `rs/` bytecode to resolve symbols. It visits named top-level/member classes, MethodInvocationTree and NewClassTree, and calls `Trees.getElement()` for the actual compiler-resolved `ExecutableElement`. Its `TypeElement` owner is converted using Java's canonical binary-name utility, preserving nested `$` class structure.

Local/anonymous class ownership and non-`rs/` targets are excluded from the exported `rs/` owner-to-owner candidate graph, while the resulting diagnostics and unresolved calls are counted as **coverage gaps**, not negative evidence.

## Why this remains incomplete

The supplied Java workspace is currently **not independently compilable**, so many source symbols may fail resolution without accepted dependencies and AST-safe remapping. R131 still surfaces conservative attributed edges, but it explicitly reports `source_callgraph_complete=false` even when source diagnostics happen to be zero: source-level method invocations and new-object expressions are not automatically equivalent to JVM-compiled callsites. The compiler may synthesize implicit constructor calls, lambda helpers and bridge methods; `invokedynamic` requires separate bootstrap analysis.

R129 must not treat a missing source edge from an unresolved symbol as an original-v309 contradiction. Before any real source↔JVM parity acceptance, the source symbol universe must be reconciled, independently validated and closed over all accepted owners/methods. Current results provide **review priority only**; no class lineage, member mapping, source rewrite or full client rebuild is accepted.

## Private invocation

```text
python -m spk_recovery.private_client_source_attributed_invokes_r131 \
  PRIVATE_V309_DECOMPILED_SOURCE.zip FRESH_PRIVATE_R131_REPORT.json \
  --source-sha256 EXACT_SOURCE_ZIP_SHA256
```

Optional `--private-identifiers` emits actual `private_source_call_edges` (same list shape as R129's `source_call_edges`), locally only. By default, all private class names and call targets are omitted; the report contains source archive pin, diagnostic and edge counts, and SHA-256 of the private edge inventory.

## Synthetic test coverage

Cross-platform Ubuntu and Windows CI uses an artificial two-class Java11 source archive with static calls, instance calls and constructors; positive edges must be **symbol-attributed**, not lexically guessed. Missing symbols remain visible as compiler errors, and no source graph completeness/original-client parity is claimed. Tests also reject duplicate edge rows, invalid Base64 and incorrect source archive SHA.

All source inputs and original JAR remain private. No independent server implementation, cache files, user account settings, or original executable Code are published.
