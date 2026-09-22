# R3B trusted class-lineage transfer

R3A describes a new build. R3B performs the first canonical migration step.

The rule is intentionally narrow:

```text
exact_sha256        -> may auto-transfer
structural_unique   -> may auto-transfer
package_anchor      -> unresolved / review
weighted_mutual_best-> unresolved / review
ambiguous           -> unresolved / review
unmatched old/new   -> unresolved / review
```

R3B composes the existing matcher, candidate builder and canonicalizer. It does not write
a second lineage mutator.

## Command

```powershell
spk-recovery update-transfer-classes `
  .\generated\v308.lineage.json `
  .\evidence\indexes\v308.json `
  .\generated\v309-intake\new-index.json `
  .\generated\v309-intake\migration-report.json `
  --old-build-id v308 `
  --new-build-id v309 `
  --new-build-number 309 `
  --out .\generated\v309.lineage.json `
  --summary-out .\generated\v309.class-transfer.json
```

The intake report is SHA/build-ID bound to both exact indexes before transfer.

The previous lineage file is never modified in place.

## Safety

- exact-byte claims are re-verified by the canonicalizer;
- unique-structural claims are re-verified by the canonicalizer;
- inferred matcher strategies are downgraded to unresolved review items;
- unmatched-new does not allocate a new logical ID;
- unmatched-old does not mark a logical class removed;
- the new build must not already exist in canonical lineage.

R3C will extend the update pipeline from class identities to persistent member identities
after the class transfer is accepted.
