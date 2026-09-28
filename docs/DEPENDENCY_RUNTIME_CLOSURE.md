# R8DEP25 runtime dependency closure

R8DEP25 is a read-only transitive runtime analysis over the R8DEP24 frontier.
It does not remove bundled classes or switch runtime packaging to official
dependency artifacts.

The analyzer starts from directly referenced bundled owners already classified
as `official_replaceable` by the private R8DEP11 replacement plan and verified
by R8DEP24. It then walks exact JVM constant-pool class/member/type references
through the bundled dependency graph.

Reachable owners are classified as:

- `official_closure_mapped` when the exact DEPREPLACE owner has a verified
  official target in its bound official artifact;
- `residual_bundled`;
- `project_retained`;
- `platform_runtime`;
- `unresolved` when no accepted replacement authority exists.

The same exact official artifact authority is re-evaluated using the
Java-release-aware artifact index used by earlier R8DEP lanes.

## Runtime resources

For official artifacts reached by the closure, the report inventories non-class
entries and separately counts:

- `META-INF/services/**` entries;
- native-looking payloads such as DLL/SO/dylib/JNI files;
- all other non-class resources.

Public reports contain only stable IDs and aggregate counts. Use
`--include-identifiers` only for private analysis.

## Safety boundary

Even a zero class-closure blocker count is not runtime replacement authority.

The report keeps `reflection_dynamic_loading_unproven=true` because ordinary
constant-pool traversal cannot prove absence of reflective/dynamic class
loading. Resource and native equivalence also remain separate gates.

Therefore this lane does not prune the dependency capsule and does not mutate
runtime packaging.

## Command

```powershell
spk-dependency-runtime-closure `
  .\private\dependency-replacement-plan.json `
  .\generated\dependency-runtime-frontier.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\dependency-runtime-closure.json
```
