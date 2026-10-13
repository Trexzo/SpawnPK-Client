# R126 — private AST declaration census for the first complete client source tree

## Why this is needed

[Issue #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004) targets the **actual** versioned, buildable `recovered-source/v309/src/` Java client—not a readable binary/JAR, decompiler archive, server emulator, or count of synthetic R125 names.

The preliminary external v309 decompiled source workspace contains **1,271 client Java compilation units**. R124 identified many `Class<number>`, `field<number>` and `method<number>` identifiers still present in that workspace. A Java filename alone does **not** establish a correspondence to an original `rs/` JVM classfile: nested classes, anonymous classes, packages, obfuscation-induced renames and shared physical source files make file counts misleading.

R126 introduces an independently SHA-pinned, **read-only source AST inventory**. It is deliberately separate from the R125 class/package/Windows naming plan, as matching spellings cannot be silently elevated to verified semantic lineage.

## Implementation

Input: an exact private decompiled-source ZIP and an **independently** SHA-256-pinned original v309 client JAR. The ZIP is validated for entry counts, duplicate paths, traversal, symlinks, UTF-8, max source size and Windows path-case collisions before any source is staged.

Only `client/src/main/java/**/*.java` (or root `src/main/java/**/*.java`) is staged in a throwaway private directory. A trusted Java helper, built from the repository's `ClientAstDeclarationCensusR126.java`, invokes JDK `JavacTask.parse()` with Java 11 source rules, **without calling task.analyze(), task.generate(), any application main, Gradle, or the original JAR**. It records Java AST top-level and explicitly declared member type identities, with proper nested `$` binary names. It intentionally excludes local and anonymous classes; those require independent compiler binary-name evidence.

The helper's private output is correlated with the original v309 `rs/` class member paths (including nested classfiles). Default output includes aggregate declaration counts, exact-spelling overlaps and mismatch counts, input SHA pins and deterministic per-Java-file content manifest hash. Optional `--private-identifiers` exposes *per-type mismatch evidence* for a subsequent reviewed class lineage solver, never for public CI or GitHub.

This audit is a **declaration coverage frontier, not a completed deobfuscation solver**. Matching names only means identical spelling. It does not prove equivalent class bodies, methods, fields, source author identity, or the candidate's ability to compile.

## Private invocation

```text
python -m spk_recovery.private_client_source_ast_census_r126 \
  PRIVATE_DECOMPILED_SOURCE.zip PRIVATE_ORIGINAL_V309.jar \
  FRESH_PRIVATE_CENSUS.json \
  --source-sha256 EXACT_PRIVATE_SOURCE_ZIP_SHA256
```

The original JAR defaults to pin `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`; the source ZIP pin must be explicit. The source ZIP is parsed, **not run**. No original `rs/` classfiles are put on the compiler classpath, and no client Java is compiled or rewritten by R126.

## Path to an actual `v309/src` release

1. Run R126 privately against the complete 1,271-source candidate and exact original. Record source declaration coverage, parsed nested declarations, all duplicate source type identities and explicit mismatch queue.
2. Reconcile unmatched declared source identities against independently accepted `CLIENT_CLASS` logical mappings and R125's Java/Windows-safe aliases. Never infer original names from lexical resemblance alone.
3. Add symbol-aware rewriting of package statements, import declarations, type/member references and constructors with AST/source-span checks. Refuse unresolved names, reflective references and collision ambiguities rather than blind source regex substitution.
4. Rebuild all client source with nonproject dependency provenance and **zero original `rs/` .class fallback**; advance deterministic compiler error triage until zero errors.
5. Independently verify full mapped class set, member/operand behavior and runtime cache/render/network-isolated acceptance, then publish the **full** source tree under existing Source Milestone/bundle gates and ensure redistribution rights.
6. For each later build, retain a standalone full Java tree and port only independently verified matching class/member identities from the prior certified snapshot.

**CI:** The checked-in tests compile the trusted AST helper and parse only synthetic Java fixture inputs. They test nested types, mismatch counts, fail-closed Java syntax, duplicate declarations, ZIP-slip/symlink and Windows casefold hazards. CI contains **no proprietary original client JAR and no real decompiled source**. No server code is included.
