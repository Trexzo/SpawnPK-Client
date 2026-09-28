# R8DEP26 runtime resource equivalence

R8DEP26 proves a narrow, read-only non-class resource boundary for official
dependencies already reached by R8DEP25.

The input closure must be the private identifier-bearing R8DEP25 report because
the public closure intentionally redacts exact artifact names. R8DEP26 emits an
identifier-free public authority by default.

For every non-class entry supplied by an official artifact used by the runtime
closure, the analyzer compares the same path against the exact bundled/readable
JAR and classifies it as:

- `exact_byte_match`;
- `service_trailing_newline_equivalent`;
- `missing_from_bundled`;
- `byte_mismatch`;
- `ambiguous_official_path` when more than one used official artifact supplies
  the same resource path.

The service normalization is intentionally narrow. It applies only under
`META-INF/services/**`, requires valid UTF-8, and accepts only one trailing LF
or CRLF difference. Other text files receive no normalization.

Native-looking payloads are reported separately. Byte equality does not prove
platform, classifier, loading, or runtime safety.

The report always keeps:

- `runtime_capsule_mutation_ready=false`;
- the R8DEP25 reflection/dynamic-loading boundary;
- native runtime safety unproven whenever a native-looking entry is present.

## Command

```powershell
spk-dependency-runtime-resource `
  .\private\dependency-runtime-closure-private.json `
  .\generated\readable-client.jar `
  --official-artifact .\private\dependencies\dependency-a.jar `
  --official-artifact .\private\dependencies\dependency-b.jar `
  --out .\generated\dependency-runtime-resource.json
```

Use `--include-identifiers` only for private inspection of exact resource
paths, providers, and hashes.
