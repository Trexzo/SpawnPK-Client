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
- round-trip authority readiness
- optional rewritten-source acceptance

It also records canonical SHA-256 digests of the exact index, class/member lineage and every
stage report so R7D can later verify reproducibility.

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
