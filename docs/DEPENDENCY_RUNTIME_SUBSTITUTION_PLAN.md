# R8DEP37 runtime dependency substitution plan

R8DEP37 is the first lane after the composed R8DEP36 readiness gate, but it is
still read-only.

The planner refuses to operate unless the supplied R8DEP36 authority reports
all of the following as true:

- `runtime_dependency_substitution_ready`;
- `class_closure_ready`;
- `dynamic_target_ready`;
- `resource_equivalence_ready`;
- `native_runtime_ready`.

It then derives an exact preimage-bound plan from private replacement authority
and private extended resource authority.

## What is planned

Only entries with explicit accepted authority are eligible:

- bundled classes whose combined DEPREPLACE/R8DEP33 classification is
  `official_replaceable`;
- bundled resources whose R8DEP35 result is either `exact_byte_match` or the
  narrowly accepted `service_trailing_newline_equivalent`, with exactly one
  official provider.

Everything else stays retained.

The planner binds:

- the exact R8DEP33 replacement extension to the exact private R8DEP34
  extended closure re-audited by R8DEP36;
- exact bundled JAR SHA-256;
- exact official artifact SHA set;
- required official artifacts;
- exact class/resource removal counts;
- protected owner classifications;
- expected bundled-entry delta;
- retained-bundled vs official and official-vs-official path collisions.

## Safety boundary

`apply_authorized=false` is unconditional in R8DEP37.

A collision-free plan is evidence for a later independently verified apply
lane. It does not modify the bundled JAR, copy official resources, remove
classes, or prune the dependency capsule.

## Command

```powershell
spk-dependency-runtime-substitution-plan `
  .\generated\runtime-readiness.json `
  .\private\dependency-replacement-plan.json `
  .\private\dependency-replacement-extension.json `
  .\private\runtime-extended-closure.json `
  .\private\runtime-extended-resource.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\runtime-substitution-plan.json
```

Use `--include-identifiers` only for the private exact entry plan.
