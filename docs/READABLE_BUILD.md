# R4B — one-command readable client build

R4B consumes one exact authority build plus **canonical ACCEPTED semantic names** and materializes a deterministic readable client JAR.

It does not create or accept names.

## Flow

```text
exact authority JAR
+ exact authority index
+ canonical class lineage
+ canonical member lineage
        |
        v
R4A semantic namespace
        |
        v
class/member remap plans
        |
        v
class risk + member safety gates
        |
        v
ASM whole-JAR rewrite
        |
        v
independent transformed verification
        |
        v
readable-client.jar + build manifest
```

## Command

```powershell
spk-readable-build `
  .\client-v308.jar `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\authority\v308-index.json `
  --build-id v308 `
  --out-dir .\generated\readable-v308
```

If accepted member renames exist, the first run intentionally stops after writing `member-safety-report.json` unless a matching explicit acceptance is supplied:

```powershell
  --member-safety-acceptance .\reviews\v308-member-safety.accepted.json
```

Class package-resource overlap and exact class-name string literals also remain explicit review gates:

```powershell
  --allow-package-resource-risk
  --rewrite-class-name-strings
```

These flags acknowledge reviewed risks; they do not create semantic acceptance.

## Workspace

The readable manifest also carries `project_source_prefixes`: the exact namespace
prefixes that remain SpawnPK project-owned after rewriting. With the R8A source-safety
fallback enabled this includes the fallback package as well as `rs/` and the semantic
target package. The fallback prefix is ownership metadata, not semantic acceptance.

A completed build contains:

```text
semantic-namespace.json
class-remap-plan.json
member-remap-plan.json
class-risk-report.json
member-safety-report.json   # when member remaps exist
readable-client.jar
remap-result.json
verification.json
readable-client-manifest.json
```

A blocked build still writes deterministic planning/risk artifacts plus a manifest with the exact blocker code. It does not create a transformed JAR.

The output directory must be empty. This prevents stale artifacts from a previous authority/namespace from being mistaken for current output.

## Statuses

- `complete` — transformed JAR exists and independent verification passed.
- `blocked` — explicit review/acceptance is required before rewriting.
- `failed` — rewriting completed but independent verification found an issue.

R4C will consume only a `complete` readable build for decompiler/source-workspace materialization.
