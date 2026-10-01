# Cross-version recovered-source delta

`spk-cross-version-source-delta` compares two independently accepted recovered Java source trees by stable `CLIENT_CLASS_*` identity.

It is deliberately downstream of the existing recovery-release gates. It does not decompile either client, accept semantic names, repair source, or infer identity.

## Required authority

Inputs:

- old `recovery_release_manifest` with `ready_for_release=true`;
- new `recovery_release_manifest` with `ready_for_release=true`;
- old `recovered_source_workspace_manifest` exactly pinned by the old release;
- new `recovered_source_workspace_manifest` exactly pinned by the new release;
- canonical `class-lineage.json` containing both builds;
- old class `remap_plan`;
- new class `remap_plan`;
- optional identifier-bearing old/new namespace-collision plans for collision-derived Source M1 trees;
- old recovered source root;
- new recovered source root.

Each source root is recomputed with the repository's canonical source-tree digest and must exactly equal its release manifest `final_source_tree_sha256`. Each recovered-source manifest must reproduce the release's `recovered_source_manifest_sha256` authority pin and `recovered_workspace_id`.

Each release authority SHA must exactly match the same build in canonical class lineage. Each remap plan must bind the same build and exact binary authority, and its deterministic digest must equal the `class_plan_digest` recorded by that recovered-source manifest. When a collision plan is supplied, it must contain exact identifiers, its readable-JAR SHA-256 must equal that release's readable-JAR authority, and its `JNSPLAN_*` ID must equal the recovered-source manifest's collision-plan authority.

The source-delta CLI rejects duplicate JSON object keys recursively across every release, recovered-manifest, lineage, remap-plan, and optional collision-plan input before authority validation. The generic historical-lineage backfill applies the same rule to current-index, class/member-lineage, and optional expected-summary JSON.

## Logical source units

Comparison is keyed by stable logical class ID, not by obfuscated filename.

For each build:

1. take the exact class-lineage entry for the logical class;
2. apply that build's class remap plan when the class was renamed for semantics or Java source safety;
3. apply that build's identifier-bearing namespace-collision plan, when the recovered tree is collision-derived;
4. derive the effective Java source path;
5. hash canonicalized Java text;
6. compare the same logical class across builds.

Nested JVM classes (`$` binary names) are intentionally not indexed as separate Java source units because the Source M1 Procyon flow reconstructs them inside the outer top-level Java unit.

The comparator fails closed if a required source unit is missing, if an unexpected `.java` file is present, if two logical classes resolve to one path, or if source-tree authority does not match the release manifest.

## Command

```powershell
spk-cross-version-source-delta `
  .\v307\recovery-release.json `
  .\v308\recovery-release.json `
  .\authority\class-lineage.json `
  .\v307\class-remap-plan.json `
  .\v308\class-remap-plan.json `
  .\v307\src `
  .\v308\src `
  --out .\v307-to-v308\source-delta.json
```

## Output

The deterministic `cross_version_source_delta` report records:

- old/new exact client authority SHA-256;
- old/new recovery release IDs;
- old/new recovered source-tree SHA-256;
- source-unit counts;
- common logical source units;
- canonical-text-identical units;
- changed units;
- logical units whose effective source path moved;
- old-only and new-only logical source units;
- deterministic `XVERSRC_*` report identity.

A changed source unit is **not automatically a semantic behavior change**. Decompiler or deterministic source-normalization output can differ even when logical bytecode identity survives. Those cases require their own provenance.

## Historical v307 -> v308 target

Exact binary authority already exists for the historical pair:

- v307: `6232bae206846a4ba8d09766a2dee886b69016066a3f50f83b201bf705f93662`
- v308: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
- archive delta authority: `XVERBIN_E56BD2FB8CCC172D6184`
- exact changed binary entry: `rs/f/a.class` only.

Historical R8 recovery provenance maps v308 `rs/f/a` to `rs/Configuration`, and the saved generated source exposes the v308 build constant as `field1628 = 308`.

The exact v307 recovered-source comparison is **not yet accepted**. A fresh v307 source tree must be independently generated with the pinned recovery/decompiler toolchain. The historical Procyon authority is:

`821da96012fc69244fa1ea298c90455ee4e021434bc796d3b9546ab24601b779`

Do not manufacture a v307 tree by copying the v308 tree and replacing the build number. That would test text editing, not recovery generality.

## Truth boundary

A `XVERSRC_*` report proves deterministic source-tree comparison across independently accepted build authorities. It does not prove inferred local or parameter names are original developer identifiers, and it does not replace the clean-rebuild or round-trip gates.

## Historical v307 -> v308 regeneration fixture

The exact private historical source-regeneration contract is pinned in `fixtures/v307-v308-source-regeneration.json`. It records the exact v307/v308 client SHA-256 pair, the already-proven one-entry binary delta, and the official Procyon v0.6.0 decompiler authority (`821da96012fc69244fa1ea298c90455ee4e021434bc796d3b9546ab24601b779`, 2,004,704 bytes).

A future exact run may use either the archived private Procyon copy or the official release artifact, but `run_decompiler()` must verify that exact SHA before execution. The fixture explicitly forbids deriving historical v307 source by editing the v308 tree; v307 must be independently regenerated from the exact v307 binary.

## Historical R8 readable-source proof

A supporting historical backtest is pinned in `fixtures/v307-v308-r8-readable-source-proof.json`.

It applies the same recovered R8 rename authority independently to the exact historical v307 and v308 client binaries. Both deterministic remapped archives contain 10,970 identical entry paths and differ in exactly one entry: the original `rs/f/a.class` update is carried into the readable identity `rs/Configuration.class`.

The exact pinned Procyon v0.6.0 decompiler then independently decompiles all 1,129 remapped project classes for each build in bounded batches. Both source trees contain the same 1,129 Java paths, zero empty files, and exactly one differing Java file: `rs/Configuration.java`. That Java delta is one assignment only: `field1628 = 307` becomes `field1628 = 308`. Canonical tree digests and byte counts are pinned in the fixture.

This is evidence that the recovered readable-name mapping survives the real v307 -> v308 client update without class-identity drift. It is deliberately **not** treated as the final modern Source-M1 historical release-manifest PASS tracked by issue #283.

## Modern historical v307 recovery-release runner

`scripts/Invoke-HistoricalV307RecoveryRelease.ps1` drives the stricter historical gate tracked by issue #283. It reuses the current recovery primitives with `build_id=v307`: exact readable authority, private namespace-collision plan, collision-derived Procyon source workspace, clean project rebuild, round-trip verification, `recovery_release_manifest`, and independent release verification.

The script pins exact v307/decompiler authority through `fixtures/v307-v308-source-regeneration.json` and refuses a source index that is not bound to the same exact v307 SHA-256. On Windows it prepares a case-sensitive output root before any recovered source is written.

The runner deliberately stops after verified historical recovery release. It does **not** call `source_milestone_cli`, build a source publication bundle, or alter the v308-only Source Milestone publication rule.

## One-command historical v307 backtest

`scripts/Invoke-HistoricalV307FullBacktest.ps1` composes the exact historical member-safety preparation and historical recovery-release runner into one fail-closed command. Its defaults point at the preserved exact-v307 backup and archived R8N private authority paths recovered from the project's local evidence.

Stage 1 must completely prepare and validate the exact v307 member-safety authority. Stage 2 then runs the modern historical recovery-release chain. Exit `3` from the release stage is preserved as `HISTORICAL_V307_BACKTEST_BLOCKED_AT_SHARED_SOURCE_FRONTIER`; this means the historical authority preparation passed but the shared Source-M1 clean-compile frontier is still blocking release readiness.

A final PASS requires the generated historical recovery manifest to report `build_id=v307` and `ready_for_release=true`. The wrapper does not invoke the v308-only Source Milestone or publication bundle path.

## Historical v307 lineage backfill

The archived canonical class/member lineage is v308-only. `spk_recovery.historical_lineage_backfill_cli` derives a temporary v307-capable lineage by running the existing R3 migration in reverse (`v308 -> v307`) against the exact historical JAR. The archived lineage files are never mutated.

The backfill uses ordinary trusted class transfer (`exact_sha256` / `structural_unique`) and builds exact member-identity candidates from the reverse class matches. The generic JAR-bound field-position proof remains unchanged and may close changed-class fields when its declaring-class own-access requirements are met. For the pinned historical v307/v308 fixture only, any residual same-symbol fields in the single fixture-proven changed project class may be carried after re-verifying the exact archive delta, old/new changed-class SHA-256 values, structural fingerprint, and complete field/method declarations. It returns usable lineage only when the ordinary authority-candidate gate reaches `ready_for_authority=true`; otherwise the migration workspace and blockers remain diagnostic evidence.

`Prepare-HistoricalV307MemberSafety.ps1` now runs this backfill before the v307 coverage gate and switches all subsequent coverage, semantic-namespace and member-safety work to the derived lineage. `Invoke-HistoricalV307FullBacktest.ps1` likewise feeds those derived lineage files into the historical recovery-release stage.

A regression mirrors the known binary shape: one same-path class changes only a `sipush`-style static build value while an unchanged class reads the affected field twice. The changed class must remain structurally unique and the unchanged class exact. Because generic field proof intentionally ignores cross-owner readers, the residual field is closed only through the fixture-bound historical carry after all exact changed-class gates pass; the generic R3 threshold is not weakened.
