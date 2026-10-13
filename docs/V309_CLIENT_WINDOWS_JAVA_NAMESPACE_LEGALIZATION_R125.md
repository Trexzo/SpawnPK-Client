# R125 — Java/Windows namespace legalization before full v309 source compilation

## Purpose

R124 independently discovered **88 original-v309 `rs/` class-versus-package shadows**, **159 case-insensitive `rs/` class-path collision groups**, and **173/1,618 corresponding whole-JAR counts**. These are JVM-legal archive identities, but cause ambiguity in Java source imports and overwrite hazards on ordinary Windows filesystems. Existing `namespace_collision_plan` and bytecode remap tools handle the *class/package* lane; they do not certify a fully Windows-safe **package-directory plus filename** namespace. R125 fills that planning gap without bypassing the existing remapper, accepted semantic lineage or source publication gates.

The R125 solver consumes a read-only **SHA-256-pinned original client JAR**. It inventories every class identity (including dependencies, because dependency package collisions may block `javac`) and constructs a deterministic **syntactic alias proposal**, in three ordered stages:

1. **Windows directory names:** where two distinct Java package prefixes have the same Unicode-casefolded path, rehome one original package subtree under a deterministic `__Pkg_<12hex>` suffix. No original class bytes or source are changed.
2. **Java type/package shadows:** where a proposed type name equals a package prefix, case-insensitively, rename the shadowing **class and its nested binary-name family** with a `__Type_<12hex>` suffix, leaving the real descendant package in place.
3. **Windows class paths:** where two proposed classfile paths still collide under casefolding, rename the noncanonical class and its nested family with a `__Case_<12hex>` suffix.

The solver **refuses** original input identities with Java-invalid identifier segments, absent/changed hash pin, duplicate ZIP members, ZIP traversal, or symlink members. It verifies after transformation that: all original class identities remain represented one-to-one, no two mapped classfile paths casefold together, no package directories casefold together, no type name shadows an actual package, and all mapped segments are syntactically Java-legal.

This is a **planning/proposal stage only**: the new names are *not* accepted semantic deobfuscated names and the tool does **not** rewrite `.java`, classfile descriptors, imports, reflective string constants, resources, or Kotlin source. Existing `collision_bytecode_remap` and `SourceNameRewriter` need to be integrated with independently reviewed class/field/method lineage; a successful plan alone is not a safe executable client and must not populate `recovered-source/v309/`.

## Private CLI

```text
python -m spk_recovery.private_client_namespace_legalizer_r125 PRIVATE_ORIGINAL_V309.jar NEW_PRIVATE_REPORT.json
```

The original SHA pin defaults to exact v309 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. For synthetic fixtures only, `--original-sha256` can select a different explicit pin.

By default the report includes only SHA pins, operation counts and the mapping digest. Add `--private-identifiers` **only for a local private output** when the subsequent, separately approved source-remapper needs the full mapping table. Do not commit that output, client JAR, original-derived source, full original class index or local asset/settings data to this repository.

## What comes next

- Replay R125 on the exact private v309 JAR and confirm the reported 88/159 baseline is represented and the solver converges. Hosted synthetic tests cannot substitute for this.
- Join proposals to accepted `CLIENT_CLASS` lineage, preserving true semantic names and consistency through nested classes, descriptors and Java declarations. Add a source-aware remap gate that rejects ambiguous/unhandled symbols, generic signatures and reflection hazards rather than regex-replacing Java text.
- Re-run a full client-only `javac` with explicit dependency provenance and **zero original `rs/` bytecode fallback**; triage errors by cause and repair existing decompiler output until compile passes.
- Prove complete original mapped class coverage, verify method and member semantics against exact v309, run cache/render startup only in isolated non-production runtime, then publish a complete `recovered-source/v309/src/` under existing Source Milestone/bundle policies.
- Once v309 is genuinely accepted, use its full-tree sources and accepted logical IDs as stable anchors for v310 onward, but run the new original-binary acceptance for every build.

**R125 is client-only.** No independently authored server modules or server reconstructions enter this lane.
