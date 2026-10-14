# R142 — three-stage original-v309 source javac measurements

The finish line is a complete, independently compilable and original-evidence-verified Java client source tree: [issue #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). R142 is **not** this finish line.

**Why:** R139 only rewrites package-changed imports. R141 rewrites R125 class-casefold simple-name aliases, but each new original-v309 javac comparison must preserve the same provisional classpath. R142 tests the same SHA-pinned private source in **three stages**: unchanged candidate, after R139 import AST repair, and after R141 import+type AST repair. Each stage is compiled using R137, with R138 collision normalization **required**, original rs game classes excluded and R136's exact known rs-linked non-rs closure excluded.

The three original client Javac error totals are comparable because the Java release, original binary hash, source coverage, dependency class-count and normalized capsule SHA must be identical. Every stage's error categories and stderr SHA are preserved privately; no compiler errors, private source names or binary bytes are committed to GitHub. If javac truncates errors due to its cap, classification is explicitly uninterpretable.

The source candidates are disposable private full-Java ZIPs. The R139 output is fed into R141; R141's input digest and source manifest MUST match R139's exact output. The source reconstruction never executes the original JAR, stage-sources, or production client. These are diagnostics using unapproved original-derived non-rs classes, not independently owned/licensed third-party dependencies.

## Exact private command

```text
python -m spk_recovery.private_v309_three_stage_javac_r142 EXACT_PRIVATE_SOURCE.zip ORIGINAL_V309.jar FRESH_PRIVATE_REPORT.json --source-sha256 2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536
```

Original JAR expected SHA-256 is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Only use an isolated private workspace, not a public Actions runner, for user original/client source inputs.

The Ubuntu and Windows tests separately compile original-like Java9 binaries for two independent collision conditions: package case variants `ext/A/...` vs `ext/a/...` (R139) and class case variants `lib/A` vs `lib/a` (R141). They prove the unchanged source fails, the R139 preview partially improves javac, and R141's type rewrite resolves the remaining synthetic error. A no-op source and bad-hash fixtures are also tested. **Passing synthetic CI does not measure real v309 javac error reductions.**

## Known real evidence and remaining gates

The earlier **614 error** real original-v309 Java diagnostic used an *unnormalized*, original-derived diagnostic capsule, not the same classpath as R142's R138 normalized comparator. It is therefore not an R142 baseline. An independent parse-only real-source screening found 47 direct affected imports in 43 Java files, of which 27 were potential conservative AST rewrite candidates, **not confirmed R141 patches**.

Real private replay must report numbers. Then continue original-derived Java source repair, reconcile class/package identities, independently own the dependency set, complete class/member original parity and offline-runtime tests, and only publish canonical `recovered-source/v309/src/` after redistribution approval. Neither clean diagnostic javac nor source-matching guesses justify release.
