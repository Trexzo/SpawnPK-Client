# R8DEP32 dynamic-only member/API transport

R8DEP32 consumes private R8DEP31 class mappings and proves whether their
declared member surface can be transported exactly to the accepted official
artifact targets.

The proof re-verifies:

- exact bundled/readable JAR authority;
- exact Java-release-aware official artifact authority;
- exact R8DEP31 old/new class structural authority;
- ordered field structure;
- ordered ordinary-method structure.

For accepted dynamic-only class mappings it then proves:

- fields by exact ordered structural position plus descriptor translation;
- ordinary methods by exact ordered structural position plus descriptor
  translation;
- constructors only by a unique translated descriptor;
- superclass/interface edges only when the mapped bundled hierarchy converges
  exactly on the official target hierarchy.

Descriptor translation may use only existing accepted class mappings from
private DEPREPLACE plus accepted R8DEP31 mappings. A descriptor that references
a bundled class with no accepted mapping fails closed.

The report distinguishes accepted identity/remap members, accepted
constructors, unresolved descriptor transport, constructor ambiguity, and
hierarchy mismatch/unresolved boundaries.

`ready_for_dynamic_root_promotion=true` is emitted only when every accepted
R8DEP31 class has complete member and hierarchy transport. This is authority to
continue the analysis pipeline; it does not mutate runtime packaging or prune
dependencies.

## Command

```powershell
spk-dependency-runtime-dynamic-member `
  .\private\dependency-runtime-dynamic-mapping.json `
  .\private\dependency-replacement-plan.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\dependency-runtime-dynamic-member.json
```

Use `--include-identifiers` only for private exact member rows.
