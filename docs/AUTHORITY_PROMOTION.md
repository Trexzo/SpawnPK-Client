# R3H — immutable authority promotion

R3E answers whether a migrated build is complete enough to become the next exact
authority. R3H turns that proof into an immutable authority snapshot.

## Command

```powershell
spk-recovery authority-promote `
  .\generated\class-lineage.json `
  .\generated\member-lineage.json `
  .\generated\new-index.json `
  .\generated\migration-report.json `
  .\generated\authority-candidate.json `
  --build-id v309 `
  --out .\authority\v309.json
```

## Fail-closed proof

The command does not trust a stored `ready_for_authority=true` flag.

It independently recomputes the R3E authority-candidate report from the supplied exact
target index, canonical class lineage, canonical member lineage and intake report. The
supplied candidate report must be byte-for-byte equivalent as a JSON value to that
recomputation and must still be ready.

A stale, edited or blocked report is refused.

## Snapshot binding

The generated `AUTHORITY_<hash>` manifest binds:

- exact target client SHA-256;
- build ID / build number / source name;
- migration ID;
- R3E authority-candidate report ID;
- previous build ID / SHA-256;
- canonical class-lineage content SHA-256;
- canonical member-lineage content SHA-256;
- exact completion summary.

The authority ID is deterministic for identical accepted inputs.

Promotion creates a new snapshot. It does not rewrite or delete the previous authority
artifact and it does not commit client binaries.
