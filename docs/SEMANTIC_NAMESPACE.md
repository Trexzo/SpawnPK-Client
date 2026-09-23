# R4A — accepted semantic namespace

R4A turns canonical **ACCEPTED** semantic names into the existing verified class/member
remap-plan formats.

It does not generate names and it does not accept candidates.

## Command

```powershell
spk-semantic-namespace `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\authority\client-index.json `
  --build-id v308 `
  --out-dir .\generated\semantic-v308
```

Outputs:

```text
semantic-namespace.json
class-remap-plan.json
member-remap-plan.json
```

The default readable class package is:

`recovered/spawnpk/client`

and can be changed with `--target-package`.

Without source-safety mode, accepted semantic classes use that global target package.
With `--source-safe-fallback`, the accepted semantic **simple name** remains authoritative
but the class stays in its exact source package. This preserves Java/JVM package-private
access while keeping semantic acceptance separate from package placement.

The namespace manifest records the active strategy as:

- `global_target_package` for the default behavior;
- `source_package_preserving` for source-safe recovery.

## Acceptance boundary

A class, field or method contributes a readable remap only when its canonical record has:

- `semantic_status = ACCEPTED`;
- a valid Java identifier semantic name;
- a confidence value in `[0, 1]`;
- non-empty semantic provenance.

`UNKNOWN` and `CANDIDATE` records remain untouched.

## Verification reuse

Class targets are passed through the existing R2A `build_remap_plan` collision and
reserved-package checks.

Member targets are passed through the existing R2C3 `build_member_remap_plan` exact
coordinate and final member namespace collision checks.

R4A therefore composes already-trusted plan builders rather than creating a weaker
parallel remap format.

## Coverage manifest

`semantic-namespace.json` records exact authority SHA, plan digests, configured target
package, semantic package strategy, and counts for total/accepted/remapped classes, fields
and methods.

An accepted name that is already identical to the obfuscated/current member spelling is
counted as accepted but does not require an executable rename row.
