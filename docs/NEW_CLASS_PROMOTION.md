# Promoting genuinely new classes

An unmatched target-build class is not automatically a new logical class.

It may instead be:

- a real newly-added client class;
- an existing logical class whose obfuscated structure changed too much for the matcher;
- an ambiguous split/merge/optimization case.

For that reason the canonicalizer stores `unmatched_new` as unresolved state.

A fresh logical ID is allocated only after explicit review:

```powershell
spk-recovery lineage-promote-new `
  .\generated\next.lineage.json `
  .\evidence\indexes\next.json `
  --build-id next `
  --path rs/some/new/class.class `
  --out .\generated\next.promoted.lineage.json
```

The promotion command requires all of the following:

1. the build already exists in canonical lineage;
2. the supplied target index SHA matches that build;
3. the path exists in that exact target index;
4. the path is not already owned by another logical class;
5. the path is currently recorded as `unmatched_new`.

Batch promotions are sorted before ID allocation, making the resulting
`CLIENT_CLASS_XXXXXX` sequence deterministic.

Promotion establishes identity only. It does not infer a semantic class name.
