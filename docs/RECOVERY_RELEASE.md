# R7A recovery release manifest

R7A collapses the already-verified R4/R5/R6 authority chain into one deterministic release
manifest. It does not perform a new remap, decompile, rebuild or source rewrite.

The command verifies that all supplied stage outputs agree on:

- exact client authority SHA
- build ID
- accepted semantic namespace
- readable JAR SHA
- recovered source workspace
- clean rebuild state
- official-first dependency transport authority/runtime boundary when present
- round-trip authority readiness
- optional rewritten-source acceptance

It also records canonical SHA-256 digests of the exact index, class/member lineage and every
stage report so R7D can later verify reproducibility. When the clean rebuild used
`official_first_restored`, R7A independently requires the R8DEP14-18 transport IDs,
artifact/hash authority, zero project fallback, compile-only official dependencies,
unchanged canonical/bundled inputs, and restored-bytecode readiness. Safe transport IDs
are then carried in `stage_ids`; private plans and paths are not copied into the release
manifest.

## Command

```powershell
spk-release-manifest `
  .\authority\v308-index.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\generated\readable-v308\readable-client-manifest.json `
  .\generated\source-v308\recovered-source-manifest.json `
  .\generated\clean-rebuild.json `
  .\generated\roundtrip.json `
  --source-rewrite-acceptance .\generated\source-rewrite-acceptance.json `
  --out .\generated\recovery-release.json
```

Exit code 0 means the supplied chain is release-ready. Exit code 3 means the documents are
internally consistent but one or more acceptance gates remain blocked. Exit code 2 means
the supplied authority chain is stale, mixed-build or malformed.

A release-ready manifest still does not claim inferred class/member/local names are original
developer identifiers.

## R7D official-first reproducibility verification

When a clean rebuild records `compile_transport.mode=official_first_restored`,
R7D requires the private and on-disk authority that was intentionally omitted
from the public release manifest. Verification is fail-closed and checks:

- the R8DEP14 overlay manifest ID, replacement-plan linkage, canonical input
  source-tree SHA and actual overlay source-tree SHA;
- the private R8DEP11 replacement plan kind/ID, bundled-readable authority and
  official artifact SHA set;
- the private R8DEP15 reverse plan kind/ID, replacement-plan linkage,
  bundled-readable authority and bytecode-restore readiness;
- the actual official dependency artifact bytes against the exact SHA set
  recorded by the clean-build transport.

The verification report records only safe IDs, booleans and hashes. It does not
copy private plan paths or identifier-bearing plan contents.

```powershell
spk-release-verify `
  .\generated\recovery-release.json `
  .\authority\v308-index.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\generated\readable-v308\readable-client-manifest.json `
  .\generated\source-v308\recovered-source-manifest.json `
  .\generated\clean-rebuild.json `
  .\generated\roundtrip.json `
  --official-overlay-manifest .\private\dependency-source-overlay-manifest.json `
  --official-overlay-source-root .\private\dependency-source-overlay\src `
  --private-dependency-replacement-plan .\private\dependency-replacement-plan.json `
  --private-dependency-reverse-plan .\private\dependency-reverse-plan.json `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\recovery-release-verification.json
```

Official-first verification inputs are accepted only for
`official_first_restored` releases. Legacy and collision-derived verification
behavior remains unchanged.

