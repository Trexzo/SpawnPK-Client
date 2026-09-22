# Canonical logical identities

Obfuscated JVM names are build-local coordinates, not project identities.

R1 introduces stable logical class IDs of the form:

```text
CLIENT_CLASS_000001
CLIENT_CLASS_000002
...
```

The initial IDs are assigned once from the immutable v308 authority by sorting the
baseline `rs/**` JVM internal names. That ordering is only a deterministic bootstrap;
the ID is thereafter persistent and is **never recomputed from a later structural hash or
obfuscated path**.

Each logical class owns a lineage array. A future matcher may attach one class location
per client build using one of these relation types:

- `BASELINE` — deterministic exact-authority seed.
- `EXACT_HASH` — byte-identical class transferred between builds.
- `STRUCTURAL` — class identity established by name-insensitive structure/evidence.
- `SEMANTIC` — identity established by stronger semantic/call-graph evidence.
- `MANUAL` — explicitly reviewed identity.

Every relation carries confidence and provenance. Low-confidence or ambiguous matches
belong in the document's `unresolved` section rather than being forced into a logical ID.

Semantic naming is separate from identity. A class can be confidently known as the same
logical class across ten builds while its readable name remains `UNKNOWN`.

## Generate the v308 seed

```powershell
spk-recovery lineage-seed .\evidence\indexes\v308.json `
  --build-id v308 `
  --build-number 308 `
  --authority EXACT_CURRENT_CLIENT `
  --out .\generated\v308.lineage.json

spk-recovery lineage-validate .\generated\v308.lineage.json
```

The generated file is intentionally not committed while this repository is public.
