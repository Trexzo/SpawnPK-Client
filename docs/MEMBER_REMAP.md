# R2C3 accepted member remap + ASM execution

R2C3 is the first stage that can turn accepted field/method semantic names into transformed
bytecode.

## Plan generation

`member-remap-plan` reads:

- canonical class lineage
- canonical member lineage
- the exact build index

Only members with `semantic_status = ACCEPTED` enter the plan. Candidate/unknown names
are ignored.

Before emitting a plan the builder verifies:

- exact index SHA matches the selected canonical build
- every source owner/name/descriptor exists in that exact index
- target names are valid Java identifiers
- accepted semantics retain provenance
- final field names do not collide inside an owner
- final method name+descriptor signatures do not collide inside an owner

## Execution

`jar-remap` may apply a class plan, a member plan, or both.

Member mappings are keyed by the exact JVM tuple:

```text
(kind, owner internal name, source name, source descriptor)
```

ASM therefore rewrites declarations and bytecode references consistently. Class and
member remaps can happen in the same pass; post-transform validation accounts for class
renames inside member descriptors.

## Reflection/name-sensitivity gate

Member names can be consumed reflectively or by name-sensitive frameworks. SpawnPK has
known reflection usage, so accepted semantic confidence alone is **not** proof that a
bytecode member rename is runtime-safe.

Therefore a member-containing `jar-remap` currently refuses by default.

Execution requires the explicit:

```text
--allow-member-reflection-risk
```

This acknowledgement is intentionally temporary. A later R2 reflection-analysis stage
should attach per-member safety evidence so proven-safe members no longer need a global
override.

## Example

```powershell
spk-recovery member-remap-plan `
  .\generated\v308.lineage.accepted.json `
  .\generated\v308.members.accepted.json `
  .\evidence\indexes\v308.json `
  --build-id v308 `
  --out .\generated\v308.member-remap-plan.json

spk-recovery jar-remap `
  .\client-v308.jar `
  .\evidence\indexes\v308.json `
  --class-plan .\generated\v308.class-remap-plan.json `
  --member-plan .\generated\v308.member-remap-plan.json `
  --allow-member-reflection-risk `
  --out .\generated\client-v308-readable.jar
```

The transformed JAR is re-indexed immediately and mapped declarations are verified before
the command reports success.
