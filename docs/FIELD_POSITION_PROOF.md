# R3M — JAR-bound exact field identity proof

R3I/R3L deliberately refuse to trust a research strategy label as field-identity
authority. R3M provides the stronger path for changed classes.

## Trust chain

```text
canonical class lineage
+ canonical CLIENT_METHOD lineage
+ exact old index + old JAR
+ exact new index + new JAR
        |
        v
recompute method-anchored field accesses from bytecode
        |
        v
unique exact access-position signatures (>=2 observations)
        |
        v
canonical CLIENT_FIELD relation
```

The proof does not trust a precomputed `exact_matched_method_access_positions` label.
It derives method correspondence from canonical `CLIENT_METHOD_*` lineage and reads both
JARs itself.

Each field signature includes:

- canonical method ID
- GET/PUT operation
- own-field access ordinal within that method
- exact bytecode offset
- normalized field descriptor identity

A field is provable only when the complete signature is unique on both sides and has at
least two observations.

## Command

```powershell
spk-field-proof-transfer `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\authority\old-index.json `
  .\generated\new-index.json `
  C:\private\client-old.jar `
  C:\private\client-new.jar `
  --old-build-id v308 `
  --new-build-id v309 `
  --out .\generated\member-lineage.proven.json `
  --proof-out .\generated\field-position-proof.json
```

Both JAR SHA-256 values must exactly match the supplied indexes and canonical builds.

## Safety

- one-observation matches are not authoritative;
- ambiguous signatures are not transferred;
- a proof cannot move a field between different canonical owner classes;
- target declarations are independently checked against the exact new index;
- a pre-existing contradictory canonical target relation is rejected;
- only matching `member_identity_review` unresolved items are removed after proof;
- client JARs remain local and are never committed.

The generated proof report is an audit artifact. The public command always recomputes it
from the exact JARs in the same operation that applies the canonical field relations.
