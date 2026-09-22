# R4E — update-aware semantic carry-forward

R4E does **not** copy semantic names from one build to another. Stable canonical class/member records already own semantic state.

Instead, R4E proves whether each `ACCEPTED` semantic record has a valid identity relation in both the previous and newly promoted authority build.

## Command

```powershell
spk-semantic-carry-forward `
  .\authority\v308.snapshot.json `
  .\authority\v309.snapshot.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\authority\v309-index.json `
  --out-dir .\generated\v309-semantic-carry
```

## Classification

For each accepted class, field and method:

- `carried` — stable ID has both previous and new build relations; semantic name can be reused.
- `blocked_missing_new_identity` — accepted in the previous authority but the stable ID has no new-build relation; do not carry the name forward.
- `available_new_only` — accepted record exists in the new authority but was not present in the previous build; this is not described as carry-forward.

The new authority snapshot must bind exactly to the supplied canonical class/member lineage digests and exact new index SHA-256.

The command also materializes the new build's R4A semantic namespace plus class/member remap plans. `ready_for_readable_build=true` only when no previously accepted semantic identity was lost across the update.
