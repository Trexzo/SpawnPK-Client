# R8DEP33 additive dynamic replacement extension

R8DEP33 composes a new replacement authority without modifying the historical
R8DEP11 `DEPREPLACE_*` plan.

It consumes:

- private R8DEP11 replacement authority;
- private R8DEP31 dynamic-only class mappings;
- matching private R8DEP32 member/API transport proof;
- the exact bundled/readable JAR;
- the exact Java-release-aware official artifact set.

A dynamic-only mapping may become an additive promoted owner only when:

1. R8DEP31 accepted the class mapping;
2. the exact R8DEP32 class row is bound to that mapping;
3. `member_transport_complete=true`;
4. the exact official target still belongs to the bound artifact;
5. no existing DEPREPLACE owner conflicts with the proposed mapping.

The original DEPREPLACE rows are never overwritten. The report emits:

- original owner authority;
- additive promoted rows;
- blocked rows;
- already-authorized rows;
- a derived combined lookup view.

The derived combined view is analysis/provenance only. It does not mutate the
runtime JAR, rewrite source, change DEPREPLACE, or authorize dependency pruning.

`ready_for_augmented_closure_reaudit=true` requires every accepted R8DEP31
mapping to be either already identically authorized or fully promotable with no
blocked/conflicting row.

## Command

```powershell
spk-dependency-replacement-extension `
  .\private\dependency-replacement-plan.json `
  .\private\dependency-runtime-dynamic-mapping.json `
  .\private\dependency-runtime-dynamic-member.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\dependency-replacement-extension.json
```

Use `--include-identifiers` only for private exact old/new owner rows.
