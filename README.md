# SpawnPK Client Recovery

Version-aware recovery tooling for the obfuscated SpawnPK JVM client.

The project is designed around **stable logical identities**, not whatever short names
ProGuard emits in one release. It fingerprints every build, reuses proven mappings across
updates, deep-analyses only real deltas, and keeps the exact client binaries outside Git.

## Current authority

Exact v308 authority:

- Library artifact: `client(6).jar`
- SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
- Main class: `rs.gui.Launcher`
- Build/config value: `308`
- Outer protocol revision: `317`

The existing SpawnPK-Src research established that v307 -> v308 changed one archive
entry (`rs/f/a.class`) and one meaningful build constant (`307 -> 308`).

## Scope

The recovery pipeline is intentionally bytecode-first:

```text
exact client JAR
  -> full index + fingerprints
  -> cross-version logical matching
  -> semantic mapping + provenance
  -> whole-JAR remap/repackage
  -> readable decompilation
  -> selective buildable source recovery
```

Original local-variable, parameter, source-file and line-number metadata was stripped
from v308. Human-readable names produced here are therefore either proven by surviving
evidence or explicitly inferred; they are not falsely presented as lost original names.

## R0 — baseline index/diff

Requirements: Python 3.11+

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

spk-recovery index C:\path\to\client-v308.jar `
  --expect-sha256 854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6 `
  --out .\evidence\indexes\v308.json
```

When the next client arrives:

```powershell
spk-recovery index C:\path\to\client-v309.jar --out .\evidence\indexes\v309.json
spk-recovery diff .\evidence\indexes\v308.json .\evidence\indexes\v309.json `
  --out .\reports\v308-to-v309.json
```

The indexer reads the whole JAR and produces both exact entry hashes and a first-pass,
name-insensitive class structural fingerprint. The matcher is deliberately conservative:
ambiguous fingerprints are reported, never guessed.

## R1 — canonical logical identities

Obfuscated paths are build-local coordinates. The canonical identity layer assigns stable
`CLIENT_CLASS_XXXXXX` IDs once from the exact v308 baseline and stores later build
locations as lineage entries with confidence + provenance. Semantic names are a separate
layer and may remain unknown even when cross-build identity is certain.

```powershell
spk-recovery lineage-seed .\evidence\indexes\v308.json `
  --build-id v308 --build-number 308 --authority EXACT_CURRENT_CLIENT `
  --out .\generated\v308.lineage.json

spk-recovery lineage-validate .\generated\v308.lineage.json
```

See `docs/LINEAGE.md` and `schemas/lineage.schema.json`.

## Repository rules

- Do not commit client JARs.
- Do not claim inferred names are original developer names.
- Preserve exact hashes for every authority build.
- Prefer deterministic mappings over editing decompiled output by hand.
- Treat decompiled/recovered source as generated until deliberately promoted.

See `docs/ARCHITECTURE.md`, `docs/UPDATE_PIPELINE.md`, and `docs/AUTHORITY.md`.
