# R2E per-member name-sensitivity safety review

Member semantic confidence is not evidence that a JVM rename is safe.

A method or field can be correctly understood yet still be observed by reflection,
framework conventions, native linkage or code outside the transformed archive.

R2E therefore inserts a review-bound safety layer between an accepted member remap plan
and bytecode mutation.

## Flow

```text
accepted member remap plan
        +
exact source JAR/index
        |
        v
member-safety-scan
        |
        v
member_safety_report
  - exact source SHA
  - exact member-plan digest
  - deterministic risk IDs
  - per-member hazards
        |
        v
human/static review
        |
        v
member_safety_acceptance
  - exact report ID
  - every exact risk ID
  - non-empty reason per decision
        |
        v
member-safety-validate
        |
        v
jar-remap
```

## Current hazards

The scanner is intentionally conservative and includes signals such as:

- native methods
- abstract/bridge methods
- public/protected/package-visible API surface
- synthetic members
- exact old member-name string literals
- old member-name literals inside classes using reflection/name lookup APIs
- owner class-name literals in reflection-heavy code
- EventBus `@Subscribe` owners

A low risk level means no current scanner hazard was detected. It does **not** prove the
rename is universally safe.

## Generate a report

```powershell
spk-recovery member-safety-scan `
  .\client-v308.jar `
  .\evidence\indexes\v308.json `
  .\generated\v308.member-remap-plan.json `
  --out .\generated\v308.member-safety.json
```

## Acceptance file

The acceptance must bind to the exact `report_id` and cover every `risk_id`:

```json
{
  "schema_version": 1,
  "kind": "member_safety_acceptance",
  "report_id": "MEMRISKREVIEW_...",
  "allow": [
    {
      "risk_id": "MEMRISK_...",
      "reason": "Reviewed exact v308 call/reflection surface; rename intentionally accepted."
    }
  ]
}
```

Validate before transforming:

```powershell
spk-recovery member-safety-validate `
  .\generated\v308.member-remap-plan.json `
  .\generated\v308.member-safety.json `
  .\generated\v308.member-safety.acceptance.json
```

Then pass both exact artifacts to the remapper:

```powershell
spk-recovery jar-remap `
  .\client-v308.jar `
  .\evidence\indexes\v308.json `
  --member-plan .\generated\v308.member-remap-plan.json `
  --member-safety-report .\generated\v308.member-safety.json `
  --member-safety-acceptance .\generated\v308.member-safety.acceptance.json `
  --out .\generated\client-v308-remapped.jar
```

## Legacy override

`--allow-member-reflection-risk` remains temporarily for compatibility, but bypasses
the per-member review evidence and should not be used for normal recovery releases.

The long-term path is to retire that global override once exact-v308 and future-build
workflows have fully migrated to report-bound acceptance.
