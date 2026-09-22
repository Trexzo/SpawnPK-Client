# R5C — progressive recovered-source compilation

R5C measures real Java buildability without pretending a partial build is a clean source rebuild.

## Strategy

Recovered Java files are compiled in deterministic batches against the verified R4 readable client JAR as an explicit fallback classpath.

If a batch compiles, every file in that batch is marked successful.

If a batch fails, it is recursively bisected until individual failing source files have isolated compiler diagnostics.

This avoids launching one `javac` process per source file while still producing file-level coverage.

## Command

```powershell
spk-progressive-compile `
  .\generated\source-v308\recovered-source-manifest.json `
  .\generated\source-v308\source-readiness.json `
  .\generated\readable-v308\readable-client-manifest.json `
  .\generated\readable-v308\readable-client.jar `
  .\generated\source-v308\build-authority.json `
  .\generated\source-v308\src `
  --batch-size 64 `
  --out-dir .\generated\source-v308\progressive
```

## Trust boundary

The command verifies:
- recovered source-tree SHA
- R5A readiness source-tree SHA
- readable fallback JAR SHA
- R5B source authority SHA
- current `javac` version and binary SHA against the R5B toolchain probe

Successful files are labeled `compiled_with_readable_fallback`.

That is deliberately **not** a clean build claim. The fallback readable JAR can satisfy references to source files that have not yet become independently compilable.

R5D removes this fallback entirely.
