# R8DEP24 runtime dependency frontier

R8DEP24 is a read-only authority over the runtime dependency capsule. It does
not remove or replace runtime classes.

It consumes the private identifier-bearing R8DEP11 replacement boundary, the
exact bundled/readable JAR, and the exact official artifacts already accepted
by that boundary. It then re-verifies the byte authorities and quantifies the
directly project-referenced bundled class entries by replacement
classification.

The report distinguishes:

- `official_replaceable` directly referenced bundled class entries and bytes;
- `residual_bundled` entries and bytes that remain protected;
- `project_retained` entries and bytes that remain protected;
- platform/runtime owners that are not bundled class entries.

Every official-replaceable target is also required to exist in its bound
official artifact.

This is deliberately **not** a pruning plan. The report always states:

- `runtime_capsule_mutation_ready=false`
- `requires_dependency_closure_proof=true`

Direct project-reference replacement does not establish transitive dependency
closure, reflection safety, service/resource equivalence, native payload
equivalence, or runtime removability.

## Command

```powershell
spk-dependency-runtime-frontier `
  .\private\dependency-replacement-plan.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\dependency-runtime-frontier.json
```

Use `--include-identifiers` only for a private local report. The default
public report retains stable owner/artifact IDs and aggregate byte counts
without exact dependency owner names.
