# R135 — first guarded Java source repair, kept private

The goal remains a complete, versioned, independently compilable **original-v309 client-only** Java source tree at `recovered-source/v309/src/` ([milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004)). R134 established a concrete source-to-original linkage candidate: the uploaded candidate's `rs/plugins/configs/ConfigPanel.java` imports `org.apache.commons.a.d_`, but the exact original client includes `org/apache/commons/a/d.class` and also classes under `org/apache/commons/a/d/`. The original `d` class declares static `a([Ljava/lang/Object;Ljava/lang/Object;)I`, matching the source call shape.

R135 **actually creates a provisional edited client Java source archive privately**, not just another candidate mapping count, and never inserts proprietary source into this GitHub repository. It limits its edit to exactly one existing candidate source file, then outputs a fresh private ZIP containing **all 1,271 client Java files and no server source**. No other Java file changes.

## Strong source and original authority checks

The private source ZIP must match its declared SHA-256 (uploaded candidate: `2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536`). The original JAR must match v309 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. The exact `ConfigPanel.java` preimage is pinned to SHA-256 `c828c1e2b9735504bdd86d18ebe8fb6699e916f13b1bd9a9c3a4f536ca719297`.

The edit requires all these independently verified conditions:

1. The R125 exact-original Java/Windows namespace mapping has a deterministic, collision-safe `d__Type_<digest>` target for the original JVM `org/apache/commons/a/d` class. No guessed `d` or `d_` spelling becomes an accepted logical ID.
2. The original verified `d.class` coexists with a `d/` package subtree and declares **exactly one static** method named `a` with JVM descriptor `([Ljava/lang/Object;Ljava/lang/Object;)I`.
3. Trusted JDK `JavacTask.parse()` (no symbol analysis against unverified external project binaries, no `generate()`) locates **exactly one** `org.apache.commons.a.d_` Java `ImportTree` and **exactly one** `d_.a((Object[])…, …)` call with two arguments. It returns only exact source offsets.
4. Python validates those AST spans against the unchanged, pinned source bytes, refuses CRLF/UTF-16 ambiguous offsets or additional `d_` references, then changes only the import and class-qualified call to the R125 alias.
5. Original/source SHA pins are rechecked. The new client-Java-only ZIP and sanitized provenance report are written to fresh private output paths. The manifest proves **1 changed Java file, 1,270 unchanged**, all inputs and outputs hashed.

The method match and parsed AST call are enough to justify a **provisional source linkage experiment**, not original JVM method-code equality. All other Java files remain byte-identical to their original uploaded candidate contents. R135 never executes the original client or the candidate, does not compile a complete client, and does not claim semantically accepted class/member lineage or original-v309 parity.

## Private command

```text
python -m spk_recovery.private_reviewed_java_alias_edit_r135 \
  PRIVATE_DECOMPILED_SOURCE.zip PRIVATE_ORIGINAL_V309.jar \
  FRESH_PRIVATE_CLIENT_JAVA_PREVIEW.zip FRESH_PRIVATE_REPORT.json \
  --source-sha256 EXACT_SOURCE_ZIP_SHA256
```

The result is a **private provisional Java working tree preview**, not a GitHub source release or proof that it compiles. This source can't yet be compiled reliably without independently resolving additional name collisions, candidate-only Gson/Lombok code, and external class provenance. The correct next step is to run a zero-original-game-class-fallback compile against an independently authorized dependency set; only verified mappings and original-derived code that pass all Source Milestone and redistribution requirements enter the canonical public source tree.

**No server reconstruction, candidate-derived original client JAR or raw assets are included in R135 GitHub changes.** CI uses two synthetic Java9 `d`/`d/Child` binaries and a synthetic source `ConfigPanel` to verify parser spans, one-file edit, changed input/hash veto, invalid original method, no class/package shadow and extra unreviewed uses.
