# R2A remap plan

Readable semantic labels are **not** automatically bytecode names.

R2A adds a separate explicit `remap_spec` keyed by stable
`CLIENT_CLASS_XXXXXX` identities. Chat 1 resolves that specification against one
exact canonical build and emits a `remap_plan` containing the verified obfuscated
source class, exact class hash and requested target JVM internal name.

## Why a separate plan?

The semantic recovery lane can suggest that a class is an
`AdventureOrbRenderer`, but that is still research output. A bytecode rename is a
separate integration decision.

This layer prevents semantic inference from silently mutating the client.

## Safety checks

Plan generation rejects:

- unknown logical IDs;
- build SHA mismatches;
- duplicate targets;
- no-op mappings;
- targets colliding with another class already present in the source build;
- dotted Java names instead of JVM internal names;
- reserved targets under `java/`, `javax/`, `jdk/` or `sun/`;
- missing confidence/provenance.

## Risk scan

Before rewriting, run:

```powershell
spk-recovery remap-risk-scan `
  .\evidence\indexes\v308.json `
  .\generated\v308.remap-plan.json `
  --out .\reports\v308.remap-risks.json
```

The current scan surfaces:

- class-name string literals that may be reflective;
- non-class resources under packages being moved;
- `META-INF/services` descriptors;
- manifest review requirements.

## Exact v308 smoke

A temporary, non-committed probe remapping only `rs/gui/Launcher`
(`CLIENT_CLASS_000196`) to `recovered/spawnpk/Launcher` produced:

```text
mapped_classes=1
literal_class_name_hit_count=0
package_resource_hit_count=1
service_descriptor_count=2
manifest_requires_review=True
```

The package-resource risk contained **5 resources** under the launcher's source
package. This is why R2A exists before R2B starts mutating JARs.

No client binary or transformed artifact is committed by this stage.
