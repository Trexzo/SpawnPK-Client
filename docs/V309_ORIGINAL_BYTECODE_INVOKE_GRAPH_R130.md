# R130 — original-v309 direct JVM invoke edge extraction

The client-side recovery milestone remains [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). The R129 review-only callgraph classifier is [#1013](https://github.com/Trexzo/SpawnPK-Client/pull/1013). R130 implements **the original-bytecode half** of the independent call-edge evidence contract; it is not another heuristic inference from class names or constant-pool-only references.

## Original input and evidence

- Read-only exact SHA-256-pinned original v309 JAR, default `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- Inventory each `rs/**/*.class` entry with duplicate/path-traversal/symlink restrictions; decode the *actual executable methods* using the existing `bytecode_profile.profile_class_field_accesses` instruction walker. Reject any header identity differing from its archive entry.
- For every **real** `invokevirtual`, `invokespecial`, `invokestatic`, or `invokeinterface` instruction, preserve the actual class owner, invocation opcode, method name/descriptor, and observed call count. Only `rs/`→`rs/` edges enter the review graph, but count all direct invocation sites for provenance.
- Track `invokedynamic` instructions **separately**, never pretending that the bootstrap target is an ordinary direct caller→callee edge. Note that a synthetic lambda implementation method may itself contain a real `invokestatic` or similar direct invocation; that direct instruction is counted, regardless of its generated method origin.
- Detect a reference to `rs/` owner class absent from the original archive; do not silently resolve it from a reconstructed client or third-party JAR.
- Verify original JAR SHA again after all reads. Read-only parser; never `java -jar` or instantiate application classes.

The default private report contains only aggregate counts, exact original-JAR digest, deterministic digest of owner-to-owner edges, and another digest of exact method-target rows. Use `--private-identifiers` **only for local private evidence** to expose `private_original_call_edges` (R129 compatible), and detailed `private_original_method_targets`. Do not upload this report with private identifiers or any original source/binary.

## Private command

```text
python -m spk_recovery.private_original_jvm_invoke_edges_r130 \
  PRIVATE_ORIGINAL_V309.jar FRESH_PRIVATE_REPORT.json
```

Or add `--private-identifiers` to keep a local full edge list. Both original and output paths are local. This tool cannot yet create the **source** side of R129's envelope; source calls need real Java AST symbol resolution, not guesses from text matching or class renaming. The **R129 matcher is therefore not yet actionable against real original-v309/source pairs** until separately SHA-pinned source edges exist. Original method call/bootstraps, class member aliases and source constructor identities remain different independent proof layers.

## Hosted tests

CI compiles a **synthetic** Java9 source with direct calls plus a lambda using `javac --release 9` on Ubuntu and Windows, checks actual direct JVM call counts and treats the invokedynamic site separately. Negative fixtures cover missing target classes, archive/header mismatch, wrong SHA, duplicate ZIP members and traversal. No private v309 JAR or proprietary Java source is checked into CI.

R130 proves only the integrity of the original-side edge parser and its contract on synthetic fixtures. It does **not** accept source-to-original class identity, source rebuild parity, any private owner source, a complete `recovered-source/v309/src/` source tree, or a runnable deobfuscated client.
