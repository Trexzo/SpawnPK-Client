# R2C canonical member lineage

Class IDs alone are not enough for long-term source recovery because ProGuard may rename
fields and methods independently between builds.

R2C therefore assigns persistent member IDs:

```text
CLIENT_FIELD_000001
CLIENT_FIELD_000002
...
CLIENT_METHOD_000001
CLIENT_METHOD_000002
...
```

The v308 baseline is seeded deterministically from the existing canonical class lineage
and exact v308 index. Fields are ordered by canonical owner class ID, obfuscated name and
descriptor. Methods use the same ordering but exclude `<init>` and `<clinit>` because
constructors are not renamable semantic members.

A member ID is assigned once. Future builds add lineage entries carrying the build-local:

- owner internal class name
- member name
- descriptor
- access flags
- method code length where available
- relation strategy
- confidence
- provenance

Semantic English names remain a separate promotion layer. Cross-build identity can be
accepted while `semantic_status` remains `UNKNOWN`.

## Baseline commands

```powershell
spk-recovery member-lineage-seed `
  .\generated\v308.lineage.json `
  .\evidence\indexes\v308.json `
  --build-id v308 `
  --out .\generated\v308.members.json

spk-recovery member-lineage-validate `
  .\generated\v308.members.json `
  --class-lineage .\generated\v308.lineage.json
```

Chat 2 member-identity reports are research candidates. Chat 1 owns the later verified
candidate-ingestion and semantic-promotion boundaries.
