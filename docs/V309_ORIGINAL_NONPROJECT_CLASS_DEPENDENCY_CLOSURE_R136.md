# R136 — Original-v309 client binary fallback contamination graph

This is an **original-client-side source-build safety gate**, not a deobfuscated source publication. The v309 decompiled source candidate still has unresolved Java compilation errors. Prior private compilation experiments depended on a derived capsule of nominally external **original** `com/`, `org/`, `gnu/`, `javax/`, and `net/` classfiles. The experiment found at least one class that directly references original `rs/` client code, so the capsule cannot be certified as an independent third-party dependency just because its filename is outside `rs/`.

R136 reads the exact SHA-256-pinned original v309 JAR **read-only** and independently checks the classfile identity of every `.class` member. Using the repository's established JVM constant-pool and classfile parsers, it collects class, member-owner, superclass/interface and field/method descriptor references. It marks as directly contaminated every non-`rs/` class that references an `rs/` original game class; the reverse dependency graph then identifies every non-`rs/` class that **transitively** depends on one of those directly contaminated classes.

This provides three distinct groups:

- **Direct dependency on original client code**: must be excluded from any attempted independent external binary-only compiler capsule.
- **Transitive dependency on original client code**: must likewise be excluded or separately recovered/replaced, even if the class contains no literal `rs/` reference itself.
- **No known graph path to original client code**: provisional candidate only. **Not automatically third-party, clean, legally redistributable, or a certified independent source-build dependency.**

All class/package names and private partition lists are omitted from the default aggregate-only report. `--private-classes` produces full identity-bearing evidence **only in the fresh local private report**; never upload it or any original classfile to public GitHub.

## Private invocation

```text
python -m spk_recovery.private_v309_dependency_closure_r136 \
  PRIVATE_ORIGINAL_V309.jar FRESH_PRIVATE_DEPENDENCY_GRAPH.json
```

The real v309 original pin defaults to `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. The optional SHA override exists for independent synthetic fixtures only. The original JAR is never executed or modified. Malformed classfiles, inconsistent class names, duplicate/unsafe archive entries, symlink entries, SHA changes and unexpectedly large classfiles fail closed.

**Critical acceptance distinction:** The dependency graph sees *static JVM references*, not reflection, service loading, resource lookup or license/provenance ownership. No non-`rs/` original class is considered approved to supply code for the recovered original client merely because its static graph is untainted. This tool does not generate a capsule, compile Java source, certify zero original-project-binary fallback, accept source↔original class identities or test a running client.

The focused Ubuntu/Windows CI compiles actual synthetic Java 9 classes: `rs.Game`, an external-named direct caller `ext.Bridge`, a transitive caller `ext.Indirect`, and an independent `ext.Clean`. It verifies graph partitioning and negative SHA, ZIP-slip, symlink, duplicate, malformed and class-name mismatch cases. No proprietary original JAR, private decompiled source or server code enters hosted CI.

## Next milestone

After the real private original-v309 replay, compare the contaminated set against the prior external binary capsule manifest. Explicitly exclude direct and transitive original-game-bound classes. Then inventory independently licensed external dependencies and source-owned files, repair genuine original v309 Java imports (R134/R135) and run a complete compiler error frontier with no original `rs/` or disguised first-party binary fallback. Follow [original client source milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).
