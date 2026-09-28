# R8DEP34 extended runtime closure re-audit

R8DEP34 re-runs the dynamic runtime closure using the additive R8DEP33
replacement extension as an authority source without modifying R8DEP11
DEPREPLACE.

It consumes private:

- R8DEP11 `DEPREPLACE_*`;
- R8DEP33 `DEPREPLACEEXT_*`;
- R8DEP25 `DEPRUNTIMECLOSURE_*`;
- R8DEP29 dynamic-target authority;

plus the exact bundled/readable JAR and the exact Java-release-aware official
artifact set.

The analyzer builds an in-memory combined mapping view from:

1. the original DEPREPLACE owner rows; and
2. only R8DEP33 `promotion_eligible` rows with complete member transport.

No input authority is rewritten.

For each proven dynamic class/service target it distinguishes:

- already present in the static closure;
- authorized by original DEPREPLACE;
- newly authorized by the replacement extension;
- remaining bundled mapping-authority gap;
- protected/non-traversable target.

Only accepted official-replaceable bundled owners are traversed. Traversal
stops at residual, project-retained, unresolved, or unclassified bundled
boundaries.

The report records how many previous R8DEP29 bundled-unclassified targets were
resolved by the extension and how many mapping gaps remain after traversing the
new roots.

Resource/native dynamic requirements are carried forward as explicit blockers;
they are not converted into class roots.

`runtime_capsule_mutation_ready=false` remains mandatory. R8DEP34 measures the
closure improvement only; it does not prune classes, replace resources, or
change runtime packaging.

## Command

```powershell
spk-dependency-runtime-extended-closure `
  .\private\dependency-replacement-plan.json `
  .\private\dependency-replacement-extension.json `
  .\private\dependency-runtime-closure.json `
  .\private\dependency-runtime-dynamic-target.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\dependency-runtime-extended-closure.json
```

Use `--include-identifiers` only for private exact root/edge rows.
