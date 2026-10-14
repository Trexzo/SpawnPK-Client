# R138 — collision-normalize the private v309 diagnostic dependency classpath

The current v309 original client source build is **not complete**. The purpose of this change is narrowly practical: reduce *false compiler errors caused by JVM-legal but Java-illegal class/package name collisions* in the unremapped original-derived provisional non-`rs/` classpath. It is not class/member semantic deobfuscation or original-game parity.

## Specific original input blocker

The actual candidate source ZIP has 1,271 Java files. Previous R137-style provisional private javac (`javac --release 11 -proc:none -implicit:none -Xmaxerrs 3000`) with original `rs/` and eight game-linked non-`rs/` binaries excluded produced **614 errors** (511 cannot-find-symbol, 58 missing-package, 45 other). Several frequently failing `gnu.trove.f.b.cc`, `gnu.trove.f.b.bU`, `gnu.trove.i.a.i` and `gnu.trove.e.a.k` classfile entries **are present in the original v309 JAR**, but a JVM permits a type such as `gnu.trove.f` to coexist with package `gnu/trove/f/b`; source javac cannot resolve that layout normally. This is a namespace collision rather than proof the import needs a new third-party library.

R138 extends the diagnostic-only R137 CLI with **`--collision-normalize-provisional-classpath`**. The private runner:

1. Pins original v309 and decompiled-source ZIPs independently; applies the R136 direct+transitive `rs/` contamination exclusions before considering bytecode rewriting.
2. Stages only the remaining provisional, original-derived non-`rs/` classfiles in a disposable **private** JAR. They are still **not certified** third-party libraries and cannot pass the final original-independent compile gate.
3. Uses the existing R125 deterministic Java/Windows-safe class-name mapping solver on that exact provisional class set and constructs an R8R-compatible private plan pinned to the staged JAR SHA and its independently computed namespace collision report ID.
4. Invokes existing R8R **whole-JAR** classfile constant-pool remapping, requiring zero post-transform namespace collisions, same class count, no game `rs/` classfile and private input/output SHA pins. It does **not** publish the transformed classfiles or original names.
5. Runs the same complete source-Java compiler diagnostic with the remapped provisional capsule. Compares aggregate counts against the unnormalized R137 report; results may improve or worsen, and neither is accepted source equivalence or safe third-party provenance.
6. Always marks `complete_original_client_source_build_accepted=false`, `original_project_binary_fallback_fully_ruled_out=false`, `candidate_source_compiled_with_independently_owned_deps=false`.

## Private invocation

Baseline:

```text
python -m spk_recovery.private_v309_compiler_frontier_r137 PRIVATE_SOURCE.zip PRIVATE_ORIGINAL_V309.jar BASELINE_PRIVATE.json --source-sha256 EXACT_SOURCE_SHA256
```

Collision-normalized candidate:

```text
python -m spk_recovery.private_v309_compiler_frontier_r137 PRIVATE_SOURCE.zip PRIVATE_ORIGINAL_V309.jar NORMALIZED_PRIVATE.json --source-sha256 EXACT_SOURCE_SHA256 --collision-normalize-provisional-classpath
```

**Synthetic cross-platform CI** compiles a JVM class `ext/a.class` and a distinct binary in package `ext/a/b/Child.class` in separate Java9 source roots. Importing `ext.a.b.Child` fails with the original unremapped classpath but succeeds after R125/R8R remaps the class blocker, without editing that import or reintroducing an excluded original `rs/` caller. Independent negative test verifies that a game-linked `ext/Bridge` binary is never supplied as a compiler fallback, even after normalization. Output ZIP hashes and mapping proof must be deterministic.

**Important:** This source import remains unchanged only because the solution renames the *colliding blocker class*, leaving the nested package path intact. Other original class mappings can require reviewed Java import/declaration edits; R135 handles one such private case and no arbitrary text substitution is approved.

The actual original-v309 **R138** replay is still a separate private acceptance task; hosted CI has no private JAR or decompiled client. A successful provisional compile would still require a **new independently owned dependency supply** and complete accepted original class/member lineage under [source milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). No server emulator/reconstruction work.
