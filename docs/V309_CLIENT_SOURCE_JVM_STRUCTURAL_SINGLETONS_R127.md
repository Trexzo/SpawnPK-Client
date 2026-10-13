# R127 — provisional source AST ↔ original JVM structural singleton matching

## Why this changes the recovery path

R126 independently parsed the **actual 1,271-file Java source candidate**: 1,321 named Java type declarations and zero syntax errors, but only **28** same-spelled class names among the 1,159 original `rs/` classfiles. The source therefore needs structural alignment before it can be transformed into a complete `recovered-source/v309/src/` tree. Blind lexical class renaming would destroy identity evidence.

R127 adds a **strictly nonauthoritative, class-shape candidate queue**. The private source ZIP and original v309 JAR must be independently SHA-256-pinned. Its trusted JDK helper parses Java syntax (`JavacTask.parse()` only, Java 11 source rules), collects declared class/interface field shapes and method signatures, normalizes reference types to `L;` while preserving primitive/array dimensions, constructor presence, and static-vs-instance distinctions. The original JVM classes are decoded independently via our existing classfile reader and normalized using equivalent descriptor rules.

The matcher considers **top-level `rs/` classes and interfaces only**: excludes named nested binary classes, enums, annotations, compiler-generated local/anonymous classes and extra JVM synthetic/bridge methods from automatic proposals because their source signatures often cannot be compared without javac lowering evidence. If a structural fingerprint occurs **exactly once** in all eligible source declarations and **exactly once** in all eligible original JVM classfiles, it yields a private *review candidate*. If any fingerprint is duplicated on either side, it yields **no** match.

## Acceptance boundary

An exact and unique field/method descriptor shape is **not proof of class identity**, and matching primitive types/staticness cannot establish method bodies, callback behavior, constant pools, opcode parity or semantic naming. Structural coincidences remain possible even for singleton shapes. R127 reports **`candidate_proposals_are_identity_accepted=false`**, **`source_files_rewritten_or_built=false`**, and **`whole_client_deobfuscation_complete=false`** always. No candidate may be fed directly to canonical lineage or rewritten Java without corroborating original-JVM method/callsite fingerprints, stable logical IDs and review.

The public default report contains only input SHA pins, aggregate counts and a deterministic private-manifest hash. `--private-identifiers` adds the individual source↔JVM proposals **only to the user's local private output**; do not paste/commit that identity-bearing list.

## Private use

```text
python -m spk_recovery.private_source_jvm_shape_singletons_r127 \
  PRIVATE_DECOMPILED_SOURCE.zip PRIVATE_ORIGINAL_V309.jar \
  FRESH_PRIVATE_SHAPE_REPORT.json \
  --source-sha256 EXACT_SOURCE_ZIP_SHA256
```

The original pin defaults to v309 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. The Java parser sees private source texts, but never executes, compiles or links them; the original binary is parsed read-only and is never executed. Hosted CI builds a tiny **synthetic original** with `javac --release 11` and verifies that a deobfuscated-name source is a *candidate* only when the structural signature is unique. It rejects ambiguities, changed primitive method shapes, wrong SHA and public identifier leakage.

## Next original-v309 client source steps

1. Replay the R127 **private actual-original** report, with all identifier-bearing proposal material withheld from public GitHub.
2. Corroborate each uniquely proposed source↔binary class with deep method operands, constants, callsite graph, and R125's Java/Windows-safe alias rules. Accept only independently unique and reviewed class lineages.
3. Feed accepted class/member mappings into AST/symbol-aware source editing, refusing class/package/import/reference ambiguities.
4. Run **whole-tree client javac** with proper provenance for external dependencies and **zero original `rs/` .class fallback**. Iterate compiler frontier until accepted clean build, mapped original class coverage and isolated local cache/runtime checks.
5. Publish a complete standalone `recovered-source/v309/src/` only after Source Milestone/bundle and redistribution approval; reuse accepted logical identities, not unreviewed heuristics, for each later build v310+.

This is strictly original **client-side** recovery. No independently implemented server code, original client JARs, cache files, or private decompiled Java are committed.
