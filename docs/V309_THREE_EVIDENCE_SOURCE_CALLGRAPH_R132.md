# R132 — join source/JVM call evidence without inventing recovered class identities

R132 wires together the exact artifacts from **R127 source↔original structural candidates**, **R130 actual original Java9 JVM invoke edges**, and **R131 Java AST symbol-attributed source invokes**, then calls the R129 **review-only** edge classifier. This is the first complete three-report integration contract for v309 class-graph triage in [source milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Required private reports and chain of custody

All three inputs must be *local, private and identifier-bearing* reports generated independently:

- **R127** `private_v309_java_ast_jvm_structural_singleton_proposals_r127`: exact source and original SHA pins, one-to-one shape candidate pairs, original class candidate names and `private_proposal_manifest_sha256`.
- **R130** `private_original_v309_jvm_invoke_edges_r130`: same original SHA, `private_original_call_edges` from executed **opcode decoding** (JAR never launched), and SHA of the exact edge list.
- **R131** `private_v309_source_ast_attributed_call_edges_r131`: same source ZIP SHA, Java compiler symbol-attributed `private_source_call_edges`, SHA of the exact list, compiler error count, unresolved source invocation count, and explicit declaration that the whole graph remains incomplete.

R132 independently recomputes **all three private-list manifest digests** and checks the version pins match exactly. It rejects missing identifiers, tampered counts/lists, version crossover and any non-bijective proposed class identity. It invokes R129's two-edge review classifier only after those gates.

Default output contains only SHA pins, private report checksums, review-only tier counts, source resolution error counts and explicit **zero accepted class identities**. Detailed source↔original name pairs are emitted only with `--private-identifiers` to a fresh **local** report; never commit that output.

## Private CLI

```text
python -m spk_recovery.private_three_evidence_callgraph_replay_r132 \
  PRIVATE_R127.json PRIVATE_R130.json PRIVATE_R131.json \
  FRESH_PRIVATE_R132_REPORT.json
```

Optional `--require-no-source-errors` rejects a source AST report with nonzero Java symbol attribution errors or unresolved calls. Use it to enforce stricter evidence when expected, **not** as a substitute for full Java compilation. The default non-strict mode preserves the unresolved counts in every output and labels the result incomplete.

## What a green R132 report does not mean

Even if **all** reported source edges match expected original owner-edge counts, there is no proof of original source method invocation opcode/target descriptor, lambda linkage, original `invokedynamic`, class/member semantic names, or exact bytecode method/code attributes. The source ZIP currently has compiler errors and potentially unresolved symbols; an absent attributed source edge must **never** be interpreted as proof that the original method does not call that class. Java compiler lowering also introduces synthetic methods and implicit invokes that AST-derived method calls do not represent identically.

R132 unconditionally marks:

- `accepted_client_class_mappings=0`
- `source_graph_semantically_equivalent_to_jvm=false`
- `source_tree_rewritten_or_compiled=false`
- `fully_deobfuscated_client_certified=false`

**Next actual source recovery stage:** independently accept original↔source **method** identities and invocation descriptors on bounded class pairs (using existing operand, CFG and verifier-frame recovery tools), then apply approved class/member mappings via AST-safe Java source editing. Reach zero-original-game-bytecode fallback full `javac` compilation before a complete `recovered-source/v309/src/` snapshot is publishable. The server and its emulator are outside this client-only scope.

Synthetic GitHub CI tests check version pin mixups, private-list mutation, strict source-error rejection and never-acceptance on Ubuntu/Windows. Private original v309 JAR, decompiled Java sources, runtime assets and local account settings stay outside public GitHub.
