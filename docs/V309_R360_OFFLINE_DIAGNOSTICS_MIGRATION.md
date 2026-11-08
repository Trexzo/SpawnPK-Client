# R360 — consolidate detached diagnostics into the correct SpawnPK-Client repository

This changeset is stacked on `research/v309-r359-loadout-dialog-readability` in `Trexzo/SpawnPK-Client`. Previous diagnostic work was mistakenly maintained in `Trexzo/fullspkclient-private` (R350), then supplied as offline ZIPs (diagnostic R351–R355). The correct source-recovery sequence already reached R359 and is independent of those duplicate R numbers. R360 restores project ownership and adds reviewed, source-only tooling under its own namespace.

## Migration manifest

| Provenance | Material moved | Limits |
| --- | --- | --- |
| Diagnostic R338/R343/R348/R349 | Prior static EOF, exact artifact, bytecode config and endpoint admission checks; synthetic test sources | Legacy original-binary execution evidence intentionally excluded |
| Diagnostic R350 | Static endpoint/cache findings documented and source-only verification tool | Private owner-PC observations not included |
| Diagnostic R351 | Denied-DNS/socket tracing logic; synthetic tests | Java SecurityManager is not OS isolation |
| Diagnostic R352 | Java harness as inspectable source; offline output/supervisor validators | Supervisor deliberately refuses every runtime launch |
| Diagnostic R353 | Bounded alias table, overflow counter, negative tests | No original binary data |
| Diagnostic R354 | Windows optional-feature inventory, strict verifier, synthetic host fixture | Feature presence never admits runtime execution |
| Diagnostic R355 | First-party bytecode invocation scanner, nominal call-path approximation, report validator and synthetic tests | Static callsites cannot prove real network traffic |

## Evidence status

- Correct-repository R359 documents private archives with 1,277 Java source files and a private reproducible build, which are not republished here; production runtime behavior remains outside the scope of this PR.
- Diagnostic R350 previously reported original v309 host `www.spawnpk.org`, login port `43594`, `user.home/.spawnpk-data` and `user.home/.spawnpk` bootstrap paths from SHA-pinned `javap` inspection. No new owner-PC replay in this migration.
- Diagnostic R346 previously observed three denied `checkConnect` checks per isolated trial, but had no verified destination for each. These do not establish three successful TCP connections.
- The scanner cannot conclude game login, original-client same-JVM reconnect, authoritative inventory recovery, or OS-enforced network isolation.
- No game binaries, private source files, owner-specific observations or live credentials are committed in R360.

## Verification and non-regression gate

Tests use synthetic Java classfiles and synthetic host receipts only. `run_r352.execute` remains disabled; CI never downloads or starts any game JAR. GitHub workflow is a tooling regression, **not** original-client acceptance. Draft/unmerged until a human reviews public-release suitability. Production v312, updater, original v309 JAR and local caches remain unchanged.

Older original-client runtime probes (R339–R341, R344–R347) are not copied to a public executable workflow. Their findings remain historical and unverified for real reconnect; importing a probe as code would not make it safe to run without OS isolation.
