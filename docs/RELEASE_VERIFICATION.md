# R7D recovery release reproducibility verification

R7D independently verifies a previously generated R7A release manifest.

At minimum it rebuilds the release manifest from the supplied exact authority documents and
requires an exact deterministic match.

Optional on-disk checks can additionally verify:

- original exact client JAR SHA-256
- readable client JAR SHA-256
- decompiler JAR SHA-256
- final recovered/rewritten Java source-tree SHA-256
- current `javac` version and binary SHA against the clean-rebuild record

## Command

```powershell
spk-release-verify `
  .\recovery-release.json `
  .\authority\v308-index.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\readable-client-manifest.json `
  .\recovered-source-manifest.json `
  .\clean-rebuild.json `
  .\roundtrip.json `
  --authority-jar .\client-v308.jar `
  --readable-jar .\readable-client.jar `
  --decompiler-jar .\tools\cfr.jar `
  --source-root .\src `
  --javac javac `
  --out .\release-verification.json
```

A mismatch is reported as `verified=false` with the exact failed check rather than silently
rebuilding or updating the release authority.

R7D verifies provenance/reproducibility. It does not make inferred semantic names more exact
than their original accepted evidence.
