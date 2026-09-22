# R5E round-trip verification

R5D proves that every project class can be rebuilt from recovered source with zero
project-class binary fallback.

R5E asks a different question:

> What did that rebuild preserve relative to the verified readable client authority?

## Classifications

Every project class is classified independently:

- `byte_identical` — exact class-entry SHA-256 equality.
- `structural_equivalent` — bytes differ but the current parser's structural
  fingerprint remains equal.
- `codegen_variance_only` — class/API/hierarchy/literal/numeric surface is equal, while
  method code lengths differ. This is recorded as compiler/decompiler codegen variance,
  not byte equivalence.
- `semantic_surface_drift` — superclass/interfaces, member signatures, access flags,
  literal strings, numeric constants, class identity/version, or unexplained structural
  state differs.

Missing or unexpected project classes are also blockers.

## Rebuild authority candidate

A report is `ready=true` only when:

- R5D says the clean project rebuild completed;
- readable and rebuilt JAR hashes match the R5D manifest;
- both JARs parse with zero class errors;
- project class sets match exactly;
- no class has semantic-surface drift.

A ready report still does **not** claim runtime equivalence when
`codegen_variance_only` exists. It is a static rebuild-authority candidate, not proof of
original source or byte-for-byte recovery.

## CLI

```powershell
spk-roundtrip-verify `
  .\clean-rebuild.json `
  .\readable-client.jar `
  .\rebuilt-client.jar `
  --out .\roundtrip-verification.json
```
