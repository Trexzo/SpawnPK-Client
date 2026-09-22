# R4C — recovered source workspace

R4C consumes only a **complete, independently verified R4B readable-client build**.

It does not rename symbols and does not accept semantic candidates.

## Command

```powershell
spk-source-workspace `
  .\generated\readable-v308\readable-client-manifest.json `
  .\generated\readable-v308\readable-client.jar `
  .\tools\cfr.jar `
  --decompiler-sha256 <PINNED_SHA256> `
  --engine cfr `
  --out-dir .\generated\source-v308
```

Vineflower and Procyon are also supported via `--engine vineflower` and `--engine procyon`. All engines remain bound to the explicitly supplied decompiler JAR SHA-256.

## Required authority pins

Before decompilation, R4C verifies:

- readable build status is `complete`
- independent R4B verification passed
- readable JAR SHA-256 matches the R4B manifest
- semantic namespace ID exists
- class remap-plan digest exists
- member remap-plan digest exists
- decompiler binary SHA-256 matches the explicitly supplied pin

## Workspace

```text
src/                              # generated Java source tree
decompiler-result.json
recovered-source-manifest.json
```

The recovered-source manifest records:

- exact source authority SHA-256
- readable transformed JAR SHA-256
- semantic namespace ID
- exact class/member plan digests
- decompiler engine + decompiler SHA-256
- Java source file count
- total generated source bytes
- deterministic source-tree SHA-256

The source-tree digest is computed over sorted relative Java paths plus exact file bytes.
It lets later stages prove they are analyzing the same decompiler output without storing the
source tree in Git.

Generated Java remains an artifact, not authoritative source and not recovered original
identifier metadata.
