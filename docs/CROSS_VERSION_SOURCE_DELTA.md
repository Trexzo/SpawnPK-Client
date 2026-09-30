# Cross-version recovered-source delta

`spk-cross-version-source-delta` compares two independently accepted recovered Java source trees by stable `CLIENT_CLASS_*` identity.

It is deliberately downstream of the existing recovery-release gates. It does not decompile either client, accept semantic names, repair source, or infer identity.

## Required authority

Inputs:

- old `recovery_release_manifest` with `ready_for_release=true`;
- new `recovery_release_manifest` with `ready_for_release=true`;
- canonical `class-lineage.json` containing both builds;
- old class `remap_plan`;
- new class `remap_plan`;
- optional identifier-bearing old/new namespace-collision plans for collision-derived Source M1 trees;
- old recovered source root;
- new recovered source root.

Each source root is recomputed with the repository's canonical source-tree digest and must exactly equal its release manifest `final_source_tree_sha256`.

Each release authority SHA must exactly match the same build in canonical class lineage. Each remap plan must bind the same build and exact binary authority. When a collision plan is supplied, it must contain exact identifiers and its readable-JAR SHA-256 must equal that release's readable-JAR authority.

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
