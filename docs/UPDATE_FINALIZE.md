# R3E authority-candidate finalization

R3E is the non-mutating completion gate for one client migration.

It answers:

> Does the exact target JAR now have complete canonical identity coverage for every
> in-scope class, field and non-constructor method?

A matcher success rate alone is not sufficient.

## Exact checks

The report requires the same target SHA-256 in:

- exact target index;
- canonical class-lineage build;
- R3A intake report.

It then enumerates the exact target JAR and compares it to canonical lineage.

## Coverage

For the configured scope (default inherited from R3A, normally `rs/`), R3E measures:

- target classes vs canonical target classes;
- target fields vs canonical target fields;
- target non-constructor methods vs canonical target methods;
- accepted semantic class names that survived into the target build;
- accepted semantic member names that survived into the target build;
- JVM class parse errors.

Constructors and static initializers are intentionally outside canonical member identity.

## Blockers

The authority candidate is blocked by:

- any target class not canonically owned;
- stale canonical target class coordinates;
- any target field/method not canonically owned;
- stale canonical target member coordinates;
- target-side ambiguous/review/new unresolved class items;
- target-side ambiguous/review/new unresolved member items;
- class parse errors.

Old-side removals are informational:

- `unmatched_old`
- `member_unmatched_old`

A removed v308 class/member does not itself prevent v309 from becoming complete.

## Command

```powershell
spk-recovery update-finalize `
  .\generated\v309.lineage.json `
  .\generated\v309.members.promoted.json `
  .\generated\v309-intake\new-index.json `
  .\generated\v309-intake\migration-report.json `
  --build-id v309 `
  --out .\generated\v309.authority-candidate.json
```

Exit codes:

- `0`: report generated and `ready_for_authority = true`;
- `1`: report generated successfully, but blockers remain;
- `2`: stale, malformed or inconsistent input.

## Important distinction

`ready_for_authority` means the recovery identity migration is complete for the exact
target client. It does not assert that every symbol has a readable English semantic name.

Semantic coverage can continue improving after identity coverage reaches 100%.
