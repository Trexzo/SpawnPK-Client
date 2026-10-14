# R133 — one-command original-v309 client source↔JVM call-graph replay

[Issue #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004) remains the definitive goal: independently accepted, complete, deobfuscated original client Java in `recovered-source/v309/src/`, compilable from source alone and suitable for isolated testing. R133 is **not** that completed tree. It makes the callgraph source-recovery review infrastructure genuinely executable from **one private command**, with no hand-assembled JSON intermediate states.

## Full guarded pipeline

Run with a private decompiled source ZIP and independent SHA-256-pinned original-v309 client JAR:

```text
python -m spk_recovery.private_client_callgraph_pipeline_r133 \
  PRIVATE_DECOMPILED_SOURCE.zip PRIVATE_ORIGINAL_V309.jar \
  FRESH_PRIVATE_REPORT.json --source-sha256 EXACT_SOURCE_SHA256
```

The original JAR pin defaults to exact v309 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. The command:

1. Requires both private files and matching SHA-256 hashes, then runs **R127** source-Java AST ↔ original JVM class-shape unique *review candidate* extraction with private identifiers retained only in memory.
2. Runs **R130** on original `rs/*.class` method `invoke*` owners via the internal constant-pool decoder; `invokedynamic` targets remain withheld.
3. Runs **R131** on private source Java through JDK11-rule `JavacTask.parse/analyze()` with **empty project dependency classpath/sourcepath**, independently resolving `Trees`/`Elements` invocation owners. Candidate Java is not generated or executed.
4. Invokes **R132** to enforce exact cross-input pins and independent row-manifest hashes before allowing the **R129** graph classifier to rank matching, contradicted and insufficient call-edge evidence.
5. Rechecks the original/source SHA pins after completion, then writes only sanitized counts and manifests by default. `--private-rows` writes individual class-pair evidence only to the fresh local private report.

**Fail-closed:** If candidate Java contains unresolved Gson/Lombok/vendor/obfuscated types, duplicate imported types, source path collisions, an unsupported Java symbol or another actual javac error, R131 aborts the pipeline before **any report is published**. The current full 1,271-file source candidate has not passed this gate. Never treat a partial source graph, fabricated parser output, a syntactically legal R125 alias or matching string literal as an accepted original class identity.

## Verified synthetic CI scope

Hosted tests compile an independent Java11 **synthetic original** from three source classes, archive the same Java source separately, run the complete pinned R127→R130→R131→R132 pipeline and assert multiple anchored edges between the same source/original class ownerships. They reject incorrect hashes and a source archive missing a necessary class, without falling back to the compiled original `rs/` classes. The default output exposes no class names. Ubuntu and Windows run these fixtures; no real private JAR, decompiled Java, user assets or account files enter CI.

This proves integration of tooling, **not** original-v309 class/member equivalence, accepted `CLIENT_CLASS` or `CLIENT_METHOD` mappings, full original source compilation, render/cache startup, or safe isolated gameplay. Next material tasks are repairing the real source candidate's Java compilation errors, feeding real fully resolved callgraph evidence into this pipeline, and accepting source/member identities by exact original bytecode/callsite parity before Java source rewriting. Subsequent v310+ builds must independently reproduce those source and original gates.
