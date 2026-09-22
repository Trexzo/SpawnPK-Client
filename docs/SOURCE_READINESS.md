# R5A — recovered-source compile-readiness audit

R5A is the first stage toward a buildable recovered client. It does not compile or edit generated source.

It re-verifies an R4C source workspace and produces a deterministic static readiness report.

## Command

```powershell
spk-source-readiness `
  .\generated\source-v308\recovered-source-manifest.json `
  .\generated\source-v308\src `
  --out .\generated\source-v308\source-readiness.json
```

## Authority checks

The exact Java source-tree SHA-256 and file count must match the R4C recovered-source manifest before analysis begins. If the generated source was edited or mixed with another decompiler run, the audit refuses it.

## Reported surfaces

- Java file/package inventory
- top-level/public type inventory
- import inventory
- probable external dependency roots
- package-path mismatches
- public type / filename mismatches
- known decompiler-failure markers
- accepted source/readable/namespace authority pins

`static_readiness_pass=true` means no high-severity static source-layout/decompiler-failure issue was detected. It does **not** mean the full source compiles; actual compiler/dependency authority is R5B/R5C.

The external-import list is a dependency discovery surface, not a Maven dependency claim. R5B must independently prove coordinates/versions before calling them exact dependencies.
