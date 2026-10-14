# R129 — source/JVM call-edge corroboration, NOT a semantic identity solver

The complete v309 deobfuscated source-tree objective remains [issue #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). R127 and R128 are merged into main; their actual private dry runs gave 501 uniquely shaped **unaccepted** class-pair proposals and 96 literal-corroborated review cases. The next check must address a distinct signal: **calls between proposed classes**.

R129 supplies a deliberately fail-closed classifier for a private, separately generated source-AST call-edge inventory and original-v309 JVM invoke-edge inventory. For each unique proposed class pair, it checks whether at least two distinct outgoing calls to *other uniquely proposed classes* have corresponding original JVM edges with no smaller observed count. Unknown/unmapped targets are excluded rather than inventing mappings. Missing/wrong counts are contradictions; zero/one matching targets are insufficient.

**Crucial limitation:** an edge between two *proposed* class pairs is not a verified independent lineage anchor. Two matching graph edges are corroborating heuristics, not proof. Matching an edge count cannot prove exact invoked method, opcode, dispatch type, lambda bootstrap or external behavior. The classifier therefore always sets `source_original_names_accepted=false`, `call_graph_equivalence_certified=false`, `method_operand_parity_proven=false`, and `whole_client_compiles_from_source=false`. This tool does **not** generate call-edge inventories or run on original client JARs by itself. A valid private evidence envelope must come from two *independent parser outputs*, each SHA-pinned, with candidate source/JVM class identities reviewed against R127/R128 output.

Private-only evidence envelope keys: `schema_version=1`, `kind=private_source_jvm_callgraph_evidence_r129`, `source_archive_sha256`, `original_client_sha256`, `source_parser_evidence_sha256`, `original_parser_evidence_sha256`, `proposals`, `source_call_edges`, `original_call_edges`. Each edge contains `caller`, `callee`, and positive `count`. Names and per-pair classification details stay private; the CLI prints sanitized aggregates and emits its full result only into a new private JSON report.

```text
python -m spk_recovery.private_client_callgraph_corroboration_r129 PRIVATE_EVIDENCE.json FRESH_PRIVATE_REPORT.json
```

Hosted Ubuntu and Windows unit tests are synthetic and contain no user source or original binary. The next engineering requirement is **source-symbol resolution and original JVM method-target extraction** (including invokedynamic/callsite semantics) to create genuine independently sourced inputs for R129. Only independently corroborated and accepted class/member mappings may proceed to source-aware Java rewriting and then a full, original-classfile-free compiler acceptance.

No server reconstruction is involved; no original client JAR, decompiled private Java or account/cache assets are committed.
