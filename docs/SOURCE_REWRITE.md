# R6C explicit source-name acceptance and rewrite

R6C is the first stage that may change generated recovered Java source.

It never consumes Chat 2 candidate files directly.

The authority chain is:

```text
R6A source-symbol inventory
    +
R6B source-name review
    +
explicit source_name_acceptance
    |
    v
source_rename_plan
    |
    v
semantic AST rewrite of a copied source workspace
```

## Acceptance

`spk-source-name-plan` accepts explicit `SRCPROP_*` proposal IDs.

Before creating a plan it verifies:

- inventory/review/acceptance IDs agree;
- proposals still target the same exact R6A symbol;
- conflicted/unknown proposals cannot be accepted;
- accepted names do not collide with another accepted target in the same source method;
- accepted names do not collide with any other existing source symbol in the same method.

The collision rule is deliberately more conservative than Java. A name already occupied
anywhere in the same source method is rejected even if two declarations might live in
disjoint sibling scopes.

## Rewrite semantics

`spk-source-rewrite` never edits the authority source directory in place.

It:

1. verifies the input Java source-tree SHA against the plan;
2. copies the entire source workspace to a new output directory;
3. uses javac's semantic AST/Element model to resolve each accepted declaration;
4. rewrites the declaration and every `IdentifierTree` bound to that exact variable element;
5. refuses overlapping/stale/missing declaration edits;
6. re-runs javac parse + semantic analysis on the rewritten workspace;
7. emits a deterministic output source-tree SHA and rewrite manifest.

This is not global text replacement. Another method can contain the same raw variable
spelling and remain untouched because it resolves to a different javac Element.

## Classpath

Recovered client source may reference bundled external dependencies.

Pass each required dependency JAR/directory explicitly:

```powershell
spk-source-rewrite .\source-rename-plan.json .\source-v308\src `
  --classpath .\clean-build\dependency-capsule.jar `
  --out-dir .\generated\source-v308-renamed
```

The rewrite manifest records the supplied classpath paths and SHA-256 for file entries.

## Commands

Create the accepted plan:

```powershell
spk-source-name-plan `
  .\source-symbols.json `
  .\source-name-review.json `
  .\source-name-acceptance.json `
  --out .\source-rename-plan.json
```

Apply it:

```powershell
spk-source-rewrite `
  .\source-rename-plan.json `
  .\source-v308\src `
  --classpath .\clean-build\dependency-capsule.jar `
  --out-dir .\generated\source-v308-renamed
```

Accepted names remain explicitly **inferred replacements**, never recovered original
parameter/local names.

R6D must still run the clean R5D build and R5E round-trip gate against the rewritten tree
before that source state is accepted as rebuild-safe.
