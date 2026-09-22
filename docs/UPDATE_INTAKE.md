# R3A automated new-build intake

R3A is the front door for a future SpawnPK client release.

It does not mutate canonical class/member lineage and it does not accept semantic names.
Its job is to turn one newly supplied client JAR into a deterministic, reviewable migration
workspace using the recovery primitives that already exist.

## Flow

```text
previous exact index + new client.jar
        |
        v
full new-JAR index
        |
        +--> archive/class diff
        |
        +--> existing cross-build class matcher
        |
        v
migration-report.json
analysis-queue.json
new-index.json
```

## Command

```powershell
spk-recovery update-intake `
  .\evidence\indexes\v308.json `
  .\client-v309.jar `
  --old-build-id v308 `
  --new-build-id v309 `
  --out-dir .\generated\v309-intake
```

The workspace contains only machine-readable analysis artifacts. The client JAR itself is
never copied into the workspace by the tool.

## Classification policy

Matches are classified conservatively:

- `byte_identical_same_path`
- `byte_identical_moved`
- `structurally_equivalent_same_path`
- `structurally_equivalent_moved`
- `package_anchor_identity_candidate`
- `weighted_identity_candidate`

Exact and unique structural matches are considered reusable identity evidence and stay out
of the focused review queue.

Package-anchor / weighted identities stay reviewable. Ambiguous, unmatched-old and
unmatched-new classes are always queued.

An unmatched-new class is **not** automatically called new code. An unmatched-old class is
**not** automatically called removed code.

## Migration ID

`MIGRATION_<hash>` is deterministic from the two exact JAR hashes, build IDs, matcher/diff
summaries and classification counts. Re-running the same intake inputs produces the same
migration identity.

## What R3A deliberately does not do

- no canonical class/member lineage mutation
- no semantic-name carry-forward yet
- no automatic new-class promotion
- no member identity transfer
- no remap/repackage

Those are later R3 integration stages after the intake report has established the exact
delta surface.
