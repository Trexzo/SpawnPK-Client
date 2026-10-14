# R132 — end-to-end private R127 + R130 + R131 call-graph evidence replay

This is the **first explicit integration gate** connecting independently derived original-v309 JVM invocations to JDK symbol-resolved decompiled Java invocations. It does not certify the entire client's identity or build.

Inputs are three separately produced private reports, with **actual SHA-256 materialized evidence, not merely a claimed same build number**:

- **R127:** source vs original field/method shape proposals, generated with `--private-identifiers`. This is a bounded, one-to-one candidate queue, **not accepted semantic names**.
- **R130:** exact pinned original v309 JVM `invoke*` owner edge report with `--private-edges`. Direct owners only; invokedynamic never guessed.
- **R131:** source Java `JavacTask.analyze()` resolved owner edge report with `--private-edges`, generated only with an **empty original-game classpath/sourcepath** and no unresolved types.

R132 independently recomputes **all three private-row manifest hashes** and compares original/source JAR/ZIP pins across input report families. It rejects reports asserting accepted class identity, executed original client, guessed dynamic targets, incomplete source symbol resolution, game-class dependency fallback, duplicate or tampered edge rows, incorrect aggregates, or unapproved source compilation claims. Only after all gates pass does it invoke the existing **R129 review-only call-edge classifier**.

The final report contains the R129 corroborated/insufficient/contradicted/no-anchor tier counts, class-pair count, input hashes, and a deterministic private result manifest. Only `--private-rows` writes per-pair names and evidence into the user's private local report. The CLI terminal output is aggregate-only even with that flag.

## Usage (private original and private candidate only)

```text
python -m spk_recovery.private_callgraph_evidence_replay_r132 \
  R127_PRIVATE_PROPOSALS.json R130_PRIVATE_ORIGINAL_EDGES.json \
  R131_PRIVATE_SOURCE_EDGES.json R132_FRESH_PRIVATE_REPORT.json
```

**Fail-closed limitation:** If the 1,271-file decompiled v309 workspace does not pass complete R131 source symbol resolution, R132 must **not** invent missing AST source edges or run with an incomplete source graph. The documented javac dependency, field/name and namespace failures remain substantial blockers; R125's syntactic aliases are not accepted semantic names. If R132 succeeds, even multi-anchor matching is still a review heuristic. JVM method invocation owner can differ from Java `Elements` declaration-owner for inheritance/interface dispatch, synthetic bridges or compiler lowering. The next acceptance layer must verify original method descriptors, full Code operands, invokedynamic BootstrapMethods, concrete callsites and verified `CLIENT_CLASS`/`CLIENT_METHOD` cross-version lineage.

None of R129–R132 rewrites original/private Java, supplies source files to a public repo, compiles a whole client, connects to production or copies private cache assets. The deliverable is still an independently accepted complete `recovered-source/v309/src/` and reproducible standalone Java source build ([source milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004)).

Hosted CI is synthetic and tests SHA mismatches, tampered rows, accepted-lineage overclaims, missing source resolution, original-binary classpath fallback and no public name leakage. **No actual original v309 executable or private Java source is uploaded to GitHub Actions.**
