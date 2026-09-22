# R2B class remap + deterministic repackaging

R2B consumes a **resolved, exact-build remap plan** produced by R2A.

It rewrites class identities only. Member names are deliberately unchanged until R2C.

## Rewritten automatically

The Java helper uses ASM `ClassRemapper` across every class in the source JAR, so
descriptors, signatures, annotations, stack-map type references, invokedynamic metadata
and ordinary JVM class references are rewritten consistently.

The repackager also rewrites:

- class entry paths
- manifest `Main-Class`
- `META-INF/services/<service type>` filenames when the service type is remapped
- provider class names inside `META-INF/services/*`

## Explicit-risk behavior

The default is fail-closed.

Exact class-name string literals are **not** rewritten unless
`--rewrite-class-name-strings` is supplied.

Non-class files located under a package containing a remapped class are never moved
implicitly. If the R2A risk scan finds such files, packaging stops unless
`--allow-package-resource-risk` is supplied after manual review.

This acknowledgement does not assert that the resources are safe. It records that the
caller deliberately accepted leaving them at their original paths.

## Determinism

Output entries are sorted lexicographically, use fixed ZIP timestamps and are stored
without compression. This makes repeated repacks byte-for-byte deterministic independent
of compressor heuristics.

## CLI

```powershell
spk-recovery class-remap `
  .\client-v308.jar `
  .\evidence\indexes\v308.json `
  .\generated\v308.remap-plan.json `
  --out .\generated\client-v308-remapped.jar `
  --result-out .\generated\client-v308-remapped.result.json
```

Risk acknowledgement is explicit:

```powershell
  --rewrite-class-name-strings
  --allow-package-resource-risk
```

The output JAR is re-indexed immediately. The command rejects entry-count drift, class
parse failures, missing target paths, stale source paths, and wrong transformed internal
names.
