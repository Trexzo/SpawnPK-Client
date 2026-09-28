# R8DEP36 runtime dependency substitution readiness

R8DEP36 is the final read-only composition gate before any explicit runtime
dependency substitution work could be considered.

It consumes:

- R8DEP34 `DEPRUNTIMEEXTCLOSURE_*`;
- R8DEP35 `DEPRUNTIMEEXTRESOURCE_*`;
- matching R8DEP29 `DEPRUNTIMEDYNAMICTARGET_*`;
- the exact bundled/readable JAR;
- the exact official artifact set.

The gate re-verifies all authority IDs and SHA bindings, then evaluates four
independent readiness domains:

- class closure;
- dynamic targets;
- non-native resource equivalence;
- native runtime safety.

Dynamic target rows are reconciled against R8DEP34 root status rather than
blindly reusing stale R8DEP29 `bundled_unclassified` counts. A target that was
later promoted by R8DEP33/R8DEP34 can therefore become resolved without
rewriting the historical R8DEP29 authority.

Project-owned and platform-runtime class targets may be considered resolved
without dependency replacement. Dependency targets require accepted static or
extended closure authority.

ServiceLoader use remains fail-closed because proving the service class token
does not prove provider discovery. Native loading also remains fail-closed.

`runtime_dependency_substitution_ready=true` requires all of the following:

- zero static/dynamic class-closure blockers;
- zero remaining mapping gaps;
- zero unresolved/protected dynamic target blockers;
- zero ServiceLoader provider-discovery blockers;
- zero blocked dynamic resource targets;
- complete non-native resource equivalence;
- zero native resource/runtime requirements.

A true result is still **not** a mutation. It only authorizes a later,
separately reviewed substitution lane.

## Command

```powershell
spk-dependency-runtime-readiness `
  .\generated\dependency-runtime-extended-closure.json `
  .\generated\dependency-runtime-extended-resource.json `
  .\generated\dependency-runtime-dynamic-target.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\dependency-runtime-readiness.json
```
