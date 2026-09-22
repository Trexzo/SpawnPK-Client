<img width="246" height="449" alt="image" src="https://github.com/user-attachments/assets/543ea4c9-38ac-44f1-8af8-98045a8d315d" />

<img width="500" height="449" alt="image" src="https://github.com/user-attachments/assets/835f4622-855b-4ff5-a9ad-64c3ea46814f" />

# SpawnPK Client Recovery

Version-aware recovery tooling for the obfuscated SpawnPK JVM client.

The project is built around **stable logical identities**, not whatever short names
ProGuard emits in one release. It fingerprints every build, transfers proven identities
across updates, deep-analyzes only real deltas, and keeps exact client binaries outside Git.

## Current authority

Exact v308 authority:

- SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
- Main class: `rs.gui.Launcher`
- Build/config value: `308`
- Outer protocol revision: `317`

The known v307 -> v308 update changed one archive entry (`rs/f/a.class`) and one
meaningful build constant (`307 -> 308`).

## What exists today

The repository now has a complete core recovery/update pipeline:

```text
exact client JAR
  -> complete index + structural fingerprints
  -> cross-build class matching
  -> stable CLIENT_CLASS identities
  -> stable CLIENT_FIELD / CLIENT_METHOD identities
  -> semantic candidate review + explicit acceptance
  -> verified class/member remap plans
  -> ASM whole-JAR rewrite
  -> deterministic repackaging
  -> independent transformed-JAR verification
  -> hash-pinned decompiler handoff
```

For future releases:

```text
previous authority + new client.jar
  -> update-migrate
  -> exact hash/index/diff
  -> trusted class-lineage transfer
  -> trusted member-lineage transfer
  -> semantic-name carry-forward only where identity survives
  -> focused unresolved/new/changed analysis queue
  -> authority-candidate completion gate
```

Unmatched or ambiguous entities remain unresolved. The tool does not invent identity just
to complete an update.

## Important naming rule

Original local-variable, parameter, source-file and line-number metadata was stripped from
v308. Readable names produced by this project are therefore either:

- supported by surviving exact evidence, or
- explicitly labeled inference/candidate names.

They are not presented as lost original source identifiers.

## Setup

Requirements:

- Python 3.11+
- JDK 21 for bytecode remapping / integration tests

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

CI runs on both Windows and Linux and includes:

- unit/integration tests
- Python compile checks
- CLI registration checks
- repository hygiene checks
- real Java/ASM remap fixtures

## R0 — exact indexing and diffing

```powershell
spk-recovery index C:\path\to\client-v308.jar `
  --expect-sha256 854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6 `
  --out .\evidence\indexes\v308.json
```

The index contains exact entry hashes, parsed class metadata, constants, strings, member
shapes and name-insensitive structural fingerprints.

## R1 — stable class identities

```powershell
spk-recovery lineage-seed .\evidence\indexes\v308.json `
  --build-id v308 `
  --build-number 308 `
  --authority EXACT_CURRENT_CLIENT `
  --out .\generated\v308.lineage.json

spk-recovery lineage-validate .\generated\v308.lineage.json
```

Canonical IDs look like:

```text
CLIENT_CLASS_000001
CLIENT_CLASS_000002
...
```

A class can retain the same logical ID even if its obfuscated path changes in a later build.

## R2 — semantic review and verified rewriting

Fields and non-constructor methods get their own stable identities:

```text
CLIENT_FIELD_000001
CLIENT_METHOD_000001
```

Semantic names remain separate from identity and require explicit review/acceptance.

Core R2 commands include:

```text
semantic-resolve
semantic-accept
remap-plan
remap-risk-scan
member-remap-plan
member-safety-scan
member-safety-validate
class-remap
jar-remap
verify-remap
decompile
```

The remapper uses ASM and rewrites JVM references consistently. Class entry paths,
manifest `Main-Class`, and `META-INF/services` entries are handled explicitly.

Member remapping has a separate name-sensitivity/reflection safety gate.

The output JAR is deterministic and is independently re-indexed/verified after rewriting.

## R3 — incremental future-update migration

The one-command migration entry point is:

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

It composes the safe automatic stages and writes a deterministic migration workspace.

A clean update can finish with:

```text
ready_for_authority=true
```

A nontrivial update can validly finish blocked with a focused review queue instead. This
is expected behavior; it prevents ambiguous/new code from silently entering canonical state.

The workspace contains:

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

The previous authority is never modified in place.

## R4 — accepted semantics to readable client/source

R4 turns one accepted authority state into reproducible readable artifacts without
weakening the review boundaries established in R1-R3.

### Readable client build

```powershell
spk-readable-build `
  .\client-v308.jar `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\authority\v308-index.json `
  --build-id v308 `
  --out-dir .\generated\readable-v308
```

This composes the accepted semantic namespace, class/member remap plans, class/member
safety gates, deterministic ASM rewrite and independent verification into one workspace.

### Recovered source workspace

```powershell
spk-source-workspace `
  .\generated\readable-v308\readable-client-manifest.json `
  .\generated\readable-v308\readable-client.jar `
  .\tools\cfr.jar `
  --decompiler-sha256 <PINNED_SHA256> `
  --engine cfr `
  --out-dir .\generated\source-v308
```

The source manifest pins the original authority SHA, transformed JAR SHA, semantic namespace,
class/member plan digests, exact decompiler SHA and a deterministic generated source-tree SHA.

### Coverage

```powershell
spk-coverage `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  --build-id v308 `
  --out .\generated\v308-coverage.json
```

Coverage keeps `ACCEPTED`, `CANDIDATE` and `UNKNOWN` separate. Only accepted names count
as remap-ready semantic coverage.

### Future-build semantic carry-forward

After a new build is promoted to exact authority:

```powershell
spk-semantic-carry-forward `
  .\authority\v308.snapshot.json `
  .\authority\v309.snapshot.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\authority\v309-index.json `
  --out-dir .\generated\v309-semantic-carry
```

Accepted names carry forward only when the same stable class/member ID has proven identity
in both authority builds. Missing new identity blocks carry-forward rather than guessing.

## Repository rules

- Do not commit client JARs or cache binaries.
- Do not commit generated/decompiled client output.
- Preserve exact SHA-256 provenance for authority builds.
- Do not claim inferred names are original developer names.
- Do not automatically promote unmatched-new classes or members.
- Do not transfer semantic names unless stable identity is proven.
- Prefer deterministic mappings over hand-editing decompiled Java.

## Documentation

Useful starting points:

- `docs/ARCHITECTURE.md`
- `docs/AUTHORITY.md`
- `docs/LINEAGE.md`
- `docs/MEMBER_LINEAGE.md`
- `docs/SEMANTIC_REVIEW.md`
- `docs/REMAP_PLAN.md`
- `docs/CLASS_REMAP.md`
- `docs/MEMBER_REMAP.md`
- `docs/MEMBER_SAFETY.md`
- `docs/VERIFY_DECOMPILE.md`
- `docs/UPDATE_INTAKE.md`
- `docs/UPDATE_TRANSFER.md`
- `docs/UPDATE_MEMBER_TRANSFER.md`
- `docs/UPDATE_FINALIZE.md`
- `docs/UPDATE_ORCHESTRATION.md`

- `docs/SEMANTIC_NAMESPACE.md`
- `docs/READABLE_BUILD.md`
- `docs/RECOVERED_SOURCE.md`
- `docs/COVERAGE.md`
- `docs/SEMANTIC_CARRY_FORWARD.md`
