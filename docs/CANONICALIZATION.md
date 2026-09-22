# Matcher -> canonical lineage boundary

The matcher is research/intelligence output. It proposes relationships.

The canonicalizer is the integration boundary. It does **not** trust a candidate report
merely because the matcher emitted it.

For every imported relationship the canonicalizer re-verifies:

- the canonical old build SHA against the supplied old index;
- candidate old/new index SHA metadata;
- old class ownership in the canonical lineage;
- old and new class paths against the supplied indexes;
- exact entry SHA equality for `exact_sha256`;
- structural fingerprint equality for `structural_unique`;
- one-to-one logical-class/target-path ownership;
- strategy score thresholds;
- target internal-name/path consistency.

Only then is a new build lineage entry attached to an existing
`CLIENT_CLASS_XXXXXX`.

## Important policy

`unmatched_new` does **not** automatically mean "new class".

It can also mean the matcher failed to correlate an existing logical class.

Therefore unmatched/ambiguous results are retained in the canonical document's
`unresolved` collection. Allocation of a brand-new logical ID requires a later,
explicit promotion/review step.

## CLI

```powershell
spk-recovery lineage-apply-candidates `
  .\generated\v308.lineage.json `
  .\evidence\indexes\v308.json `
  .\evidence\indexes\next.json `
  .\reports\v308-to-next.candidates.json `
  --old-build-id v308 `
  --new-build-id next `
  --new-authority EXACT_CURRENT_CLIENT `
  --out .\generated\next.lineage.json

spk-recovery lineage-validate .\generated\next.lineage.json
```

The matcher and canonicalizer intentionally remain separate modules so future semantic
or AI-assisted matchers cannot silently weaken persistent lineage guarantees.
