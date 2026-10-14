# R141 — actual Java type-use rewrite for v309 class casefold aliases

**Client-side original-derived source recovery only.** Stacked on R140 #1027 → R139 #1026 → R138 #1025 → R137 #1024 → R136 #1023. Full client source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

A separate PRIVATE, read-only audit using the **exact** original-v309 class inventory and uploaded 1,271-client-Java source ZIP found **1,459** case-insensitive name-collision groups among original non-rs binary classfiles. The lexicographic noncanonical side of those groups appears in **47 explicit non-static Java imports across 43 source files** (16 distinct imported class identities). The same non-rs original archive has **zero** casefold-colliding package-directory groups. R139's package-only import rewrite therefore cannot be assumed to solve these actual class-name collisions.

**R141 implements a real Java source edit stage** for imported class types renamed by R125's `windows_class_case` class-leaf rule. It uses only R136's pinned provisional non-rs dependency partition and exact R125 mapping, not guessed alias spellings. A new trusted JDK `JavacTask.parse()` helper identifies the explicit import position and enumerates Java `IdentifierTree` occurrences matching the original class leaf. Only syntactically provable **type** sites (declarations, return/parameter types, new expressions, supported generic/array/annotation/type contexts) are replaced together with the exact import, in a fresh private full-Java ZIP. The file is untouched if there is a static/expression receiver, source-local shadow type or type parameter, more than one eligible import, an import collision or unresolved source-offset safety issue. It rejects source-original hash drift.

## Cross-platform synthetic proof

The Ubuntu+Windows fixture compiles two original Java9 binary classes separately whose paths differ only by case but cannot both be represented without a name alias. It generates the real R125/R138 normalized classpath, demonstrates javac fails for the old import/type references, runs R141's JDK AST rewrite, and compiles the repaired Java source against exactly the R138 mapping, without any original `rs/` game-class binary fallback. Ambiguous static receivers, type-parameter shadowing and bad source/original hashes are negative controls.

This is a bounded proof of an **actual source-changing mechanism**. Its exact real-v309 source replay and number of safely edited real files still need measurement. No claim of full client compilability or semantic original class/member identity is made.

## Private use

```text
python -m spk_recovery.private_v309_casefold_type_rewrite_r141 PRIVATE_DECOMPILED_SOURCE.zip PRIVATE_ORIGINAL_V309.jar FRESH_PRIVATE_EDITED_SOURCE.zip FRESH_PRIVATE_REPORT.json --source-sha256 EXACT_SOURCE_ZIP_SHA256
```

Report records input SHA pins, changed/unchanged files, changed imports/type references, withheld ambiguous files, original R125 mapping digest and explicit non-certification flags. Never publish original-derived candidate Java, original JAR, project runtime assets/accounts, identifier-bearing maps, or derived classfiles. Even a clean diagnostic javac run against the provisional original-derived non-rs classpath would not prove independently owned dependencies, semantic original parity, runtime equivalence, or redistribution rights.

Final target remains `recovered-source/v309/src/` as a complete, independently compilable, verified Java client snapshot.
