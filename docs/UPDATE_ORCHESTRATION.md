# R3F — one-command update migration

R3A–R3E deliberately keep each trust boundary independent. R3F composes those stages into
one repeatable workspace command without weakening any of them.

## Command

```powershell
spk-recovery update-migrate `
  .\authority\previous-index.json `
  .\client-new.jar `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  --old-build-id v308 `
  --new-build-id v309 `
  --new-build-number 309 `
  --member-candidates .\research\v308-to-v309.members.json `
  --out-dir .\generated\migration-v309
```

## Automatic stages

1. hash + fully index the new JAR;
2. produce the R3A archive/class delta and focused class queue;
3. transfer only exact-SHA and unique-structural class identities;
4. optionally transfer only trusted member identities from an explicit candidate report;
5. preserve accepted semantic names only because the stable identity survived;
6. run the R3E authority-candidate completion gate;
7. consolidate target-side class/member unresolved work into one focused queue.

## Fail-closed review policy

The coordinator never:

- promotes unmatched-new classes;
- promotes unmatched-new fields/methods;
- accepts English semantic names;
- upgrades package-anchor or weighted class matches to authority;
- upgrades usage-context member inference to authority.

Those remain explicit review/promotion operations.

If member candidates are not supplied, class migration still runs, but the workspace is
blocked and the focused queue contains `member_identity_candidates_required`.

## Exit behavior

- `0`: migration completed and target is a complete authority candidate;
- `1`: migration completed but explicit review/promotion is still required;
- `2`: stale/invalid/mismatched input.

A blocked migration is therefore a valid result, not a crash.

## Workspace

The command writes:

```text
new-index.json
migration-report.json
analysis-queue.json
class-lineage.json
member-lineage.json
class-transfer-summary.json
member-transfer-summary.json
authority-candidate.json
focused-analysis-queue.json
migration-workspace.json
```

The previous authority files are never modified in place.
