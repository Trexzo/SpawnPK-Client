# R144 — atomic multi-import AST source repair

Original v309 client Java (not server code), stacked on R143 [#1030](https://github.com/Trexzo/SpawnPK-Client/pull/1030) / R142 [#1029](https://github.com/Trexzo/SpawnPK-Client/pull/1029) / milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

The R141/R143 combined type-alias source stage previously refused **any** Java file with two eligible imports. That was safe but prevented useful original-source compilation recovery. The exact-private source audit of the original 1,271-file v309 ZIP identified **six** files with two or more R125 casefold/shadow-renamed nonstatic class imports; **five** met a conservative no-duplicate-simple-name/no-multiple-qualified-occurrence prescreen. No original source files or names have been posted publicly.

R144 makes the full-source Java transformation **atomic per file**:

1. Take the exact whole-file UTF-8 candidate, source manifest and original-v309 SHA-pinned R125/R136 mapping, with the same unchanged compiler.
2. Up to eight independently mapped imports may be considered together only when *all* old and proposed simple names are pairwise distinct and do not collide with any other imported type. Repeated imports remain disallowed.
3. Run the trusted parse-only JDK `JavacTask` helper separately for each imported original type, **always against exactly the same original, unedited Java bytes**. Require a single matching explicit import, the exact original source span, and only syntactically proven type-identifier uses. Any static/expression receiver, local type shadow, ambiguous fully qualified use, syntax discrepancy, offset discrepancy, imported-name collision or path issue vetoes the **entire** source file.
4. If and only if all imports pass, check global AST span disjointness, apply a single sorted reverse-position patch transaction, and validate all proposed imports are present and all old imports absent. This cannot partially repair a Java file.
5. Return original+updated full-Java source candidate file sets and the usual sanitized source manifest/count evidence. No original game class binary fallback, private original-derived source publication or semantic equivalence claim.

Cross-platform synthetic CI independently compiles both JVM class-case variants (`lib/A` + `lib/a`) and a JVM class/package shadow (`lib/node.class` + `lib/node/Child.class`). One Java source imports both aliased classes. Unchanged javac fails; atomic R144 JDK-AST repaired source compiled against R138's exact temporary remapped capsule must succeed; R142 three-stage diagnostic error count decreases. Negative controls ensure that even when the first import is safely mapped, an ambiguous second import vetoes **all** source edits. R141, R143 and R142 regressions also run.

**Private real-v309 measurement still pending for this exact GitHub code.** Prior independent two-pass private reproduction achieved 625 → 534 → 524 errors against one locally reconstructed, uncertified, original-derived non-rs capsule; it modified **30 distinct files, 31 imports and 67 type sites**, as one file was modified across both source-repair passes. This is not the exact combined per-file R144 pipeline, and a favorable compiler delta alone never proves complete client compilability or independent dependency provenance. The earlier 614-error baseline is from an unnormalized capsule and is not comparable.

The recovered-source/v309/src tree remains incomplete. Neither automatic merge nor declaring release rights is justified by a synthetic JDK success.
