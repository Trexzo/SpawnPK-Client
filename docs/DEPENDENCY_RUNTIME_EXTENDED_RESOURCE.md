# R8DEP35 extended runtime resource equivalence

R8DEP35 extends the R8DEP26 non-class resource audit to the effective artifact
set used after R8DEP33/R8DEP34 dynamic-root promotion.

It consumes private:

- R8DEP34 `DEPRUNTIMEEXTCLOSURE_*`;
- original R8DEP26 `DEPRUNTIMERESOURCE_*`;

plus the exact bundled/readable JAR and the complete official artifact set.

The analyzer preserves an R8DEP26 resource row only when:

- the exact resource path is unchanged;
- the exact provider artifact set is unchanged;
- the status is unchanged;
- service/native classification is unchanged.

If a newly used artifact introduces the same path, the path is recomputed
against the full extended provider set. This prevents an old exact match from
hiding a new cross-artifact ambiguity.

Newly used artifacts are audited with the same narrow rules as R8DEP26:

- exact bytes;
- UTF-8 `META-INF/services/**` trailing LF/CRLF equivalence only;
- missing from bundled;
- byte mismatch;
- ambiguous official path.

Duplicate JAR resource entries fail closed.

Native-looking payloads are inventoried separately. Even exact native bytes do
not establish platform/classifier/runtime safety.

`resource_equivalence_complete=true` means every used **non-native** resource
is exact or narrowly service-equivalent and no non-native ambiguity/mismatch is
present. Native runtime safety remains a separate blocker.

Runtime capsule mutation remains disabled.

## Command

```powershell
spk-dependency-runtime-extended-resource `
  .\private\dependency-runtime-extended-closure.json `
  .\private\dependency-runtime-resource.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\dependency-runtime-extended-resource.json
```

Use `--include-identifiers` only for private exact resource/provider rows.
